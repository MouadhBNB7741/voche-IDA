"""
Trial sync and alert matching.

- run_sync(): pulls recruiting studies from ClinicalTrials.gov API v2 for the configured
  conditions, normalizes them into clinical_trials (+ trial_sites), upserts by nct_id and
  records the run in trial_sync_logs.
- notify_matches(): when a trial is new or becomes Recruiting, notifies users whose
  trial_alerts or profile interests match it. Each user hears about a trial once.
"""
import json
import logging
import re
from datetime import date
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from app.core.config import settings
from app.db.postgres import PostgresDB
from app.schemas.notification import NotificationType
from app.services.email import EmailService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

CT_API_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 50
MAX_SITES_PER_TRIAL = 25
SYNC_LOCK_ID = 74210301  # pg advisory lock: only one sync at a time across all API processes

STATUS_MAP = {
    "NOT_YET_RECRUITING": "Not yet recruiting",
    "RECRUITING": "Recruiting",
    "ENROLLING_BY_INVITATION": "Active",
    "ACTIVE_NOT_RECRUITING": "Active",
    "COMPLETED": "Completed",
    "SUSPENDED": "Suspended",
    "TERMINATED": "Terminated",
    "WITHDRAWN": "Terminated",
}
PHASE_MAP = {"EARLY_PHASE1": "Phase 1", "PHASE1": "Phase 1", "PHASE2": "Phase 2", "PHASE3": "Phase 3", "PHASE4": "Phase 4"}

Fetcher = Callable[[str], Awaitable[List[Dict[str, Any]]]]


# ---------------------------------------------------------------- normalization

def parse_age(text: Optional[str]) -> Optional[int]:
    """'18 Years' -> 18, '6 Months' -> 0, 'N/A' or None -> None."""
    m = re.match(r"\s*(\d+)\s*(\w+)", text or "")
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2).lower()
    return value if unit.startswith("year") else 0


def parse_date(text: Optional[str]) -> Optional[date]:
    """ClinicalTrials.gov dates are 'YYYY-MM' or 'YYYY-MM-DD'."""
    if not text:
        return None
    parts = text.split("-")
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 1)
    except (ValueError, IndexError):
        return None


def normalize(study: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map one API v2 study to our columns. None when it cannot fit our schema (no phase, unknown status)."""
    p = study.get("protocolSection", {})
    ident, status_mod = p.get("identificationModule", {}), p.get("statusModule", {})
    design, elig = p.get("designModule", {}), p.get("eligibilityModule", {})
    conditions = p.get("conditionsModule", {}).get("conditions") or []

    nct_id, title = ident.get("nctId"), ident.get("briefTitle")
    status = STATUS_MAP.get(status_mod.get("overallStatus"))
    phases = [PHASE_MAP[ph] for ph in design.get("phases") or [] if ph in PHASE_MAP]
    if not (nct_id and title and status and phases and conditions):
        return None

    sites = []
    for loc in p.get("contactsLocationsModule", {}).get("locations") or []:
        if loc.get("city") and loc.get("country"):
            sites.append({
                "site_name": (loc.get("facility") or loc["city"])[:255],
                "city": loc["city"][:100],
                "country": loc["country"][:100],
                "is_recruiting": loc.get("status", "RECRUITING") == "RECRUITING",
            })
        if len(sites) == MAX_SITES_PER_TRIAL:
            break

    rules = {
        "min_age": parse_age(elig.get("minimumAge")),
        "max_age": parse_age(elig.get("maximumAge")),
        "gender": (elig.get("sex") or "ALL").lower(),
        "conditions": conditions,
        "inclusion_list": [],
        "exclusion_list": [],
    }
    return {
        "nct_id": nct_id,
        "title": title[:500],
        "summary": p.get("descriptionModule", {}).get("briefSummary"),
        "disease_area": conditions[0][:255],
        "phase": max(phases),  # combined phases such as PHASE1/PHASE2 are filed under the later one
        "status": status,
        "sponsor": (p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name") or "Unknown")[:255],
        "countries": sorted({s["country"] for s in sites}),
        "eligibility_criteria": elig.get("eligibilityCriteria"),
        "eligibility_rules": {k: v for k, v in rules.items() if v is not None},
        "start_date": parse_date(status_mod.get("startDateStruct", {}).get("date")),
        "estimated_completion": parse_date(status_mod.get("completionDateStruct", {}).get("date")),
        "max_enrollment": design.get("enrollmentInfo", {}).get("count"),
        "metadata": {"source_url": f"https://clinicaltrials.gov/study/{nct_id}"},
        "sites": sites,
    }


# ---------------------------------------------------------------- fetching

async def fetch_from_clinicaltrials_gov(condition: str) -> List[Dict[str, Any]]:
    """Recruiting / not-yet-recruiting studies for one condition, up to the configured cap."""
    studies: List[Dict[str, Any]] = []
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
        "pageSize": PAGE_SIZE,
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        while len(studies) < settings.trial_sync_max_per_condition:
            res = await client.get(CT_API_URL, params=params)
            res.raise_for_status()
            data = res.json()
            studies.extend(data.get("studies", []))
            if not data.get("nextPageToken"):
                break
            params["pageToken"] = data["nextPageToken"]
    return studies[: settings.trial_sync_max_per_condition]


# ---------------------------------------------------------------- storing

async def upsert_trial(conn, t: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update by nct_id and replace its sites. Returns {trial_id, inserted, became_recruiting}."""
    async with conn.transaction():
        previous = await conn.fetchval("SELECT status FROM clinical_trials WHERE nct_id = $1", t["nct_id"])
        row = await conn.fetchrow(
            """
            INSERT INTO clinical_trials (
                nct_id, title, summary, disease_area, phase, status, sponsor, countries,
                eligibility_criteria, eligibility_rules, start_date, estimated_completion,
                max_enrollment, metadata, sync_source, last_synced_at, last_updated
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10::jsonb, $11, $12, $13, $14::jsonb,
                    'clinicaltrials_gov', NOW(), NOW())
            ON CONFLICT (nct_id) DO UPDATE SET
                title = EXCLUDED.title, summary = EXCLUDED.summary, disease_area = EXCLUDED.disease_area,
                phase = EXCLUDED.phase, status = EXCLUDED.status, sponsor = EXCLUDED.sponsor,
                countries = EXCLUDED.countries, eligibility_criteria = EXCLUDED.eligibility_criteria,
                eligibility_rules = EXCLUDED.eligibility_rules, start_date = EXCLUDED.start_date,
                estimated_completion = EXCLUDED.estimated_completion, max_enrollment = EXCLUDED.max_enrollment,
                metadata = clinical_trials.metadata || EXCLUDED.metadata,
                sync_source = 'clinicaltrials_gov', last_synced_at = NOW(), last_updated = NOW()
            RETURNING trial_id
            """,
            t["nct_id"], t["title"], t["summary"], t["disease_area"], t["phase"], t["status"], t["sponsor"],
            json.dumps(t["countries"]), t["eligibility_criteria"], json.dumps(t["eligibility_rules"]),
            t["start_date"], t["estimated_completion"], t["max_enrollment"], json.dumps(t["metadata"]),
        )
        trial_id = row["trial_id"]
        await conn.execute("DELETE FROM trial_sites WHERE trial_id = $1", trial_id)
        if t["sites"]:
            await conn.executemany(
                "INSERT INTO trial_sites (trial_id, site_name, city, country, is_recruiting) VALUES ($1, $2, $3, $4, $5)",
                [(trial_id, s["site_name"], s["city"], s["country"], s["is_recruiting"]) for s in t["sites"]],
            )
    return {
        "trial_id": trial_id,
        "inserted": previous is None,
        "became_recruiting": t["status"] == "Recruiting" and previous != "Recruiting",
    }


async def run_sync(conn, fetch: Optional[Fetcher] = None, log_id=None) -> Dict[str, Any]:
    """One sync run. Uses an existing trial_sync_logs row when log_id is given (admin trigger)."""
    fetch = fetch or fetch_from_clinicaltrials_gov
    if log_id is None:
        log_id = await conn.fetchval("INSERT INTO trial_sync_logs DEFAULT VALUES RETURNING id")
    fetched = inserted = updated = 0
    problems: List[str] = []
    to_notify = []
    try:
        for condition in [c.strip() for c in settings.trial_sync_conditions.split(",") if c.strip()]:
            studies = await fetch(condition)
            fetched += len(studies)
            for study in studies:
                trial = normalize(study)
                if trial is None:
                    continue
                try:
                    result = await upsert_trial(conn, trial)
                except Exception as e:  # one bad record must not stop the run
                    problems.append(f"{trial['nct_id']}: {e}")
                    continue
                inserted += result["inserted"]
                updated += not result["inserted"]
                if result["inserted"] or result["became_recruiting"]:
                    to_notify.append(result["trial_id"])
        status, error = "success", "\n".join(problems[:50]) or None
    except Exception as e:
        logger.error(f"Trial sync failed: {e}")
        status, error = "failed", str(e)

    await conn.execute(
        """
        UPDATE trial_sync_logs SET sync_completed_at = NOW(), records_fetched = $2, records_inserted = $3,
            records_updated = $4, status = $5, error_details = $6
        WHERE id = $1
        """,
        log_id, fetched, inserted, updated, status, error,
    )
    for trial_id in dict.fromkeys(to_notify):
        await notify_matches(conn, trial_id)
    logger.info(f"Trial sync {status}: fetched={fetched} inserted={inserted} updated={updated}")
    return dict(await conn.fetchrow("SELECT * FROM trial_sync_logs WHERE id = $1", log_id))


async def scheduled_sync():
    """Cron entry point. Off unless TRIAL_SYNC_ENABLED=true; one process at a time via advisory lock."""
    if not settings.trial_sync_enabled:
        return
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT pg_try_advisory_lock($1)", SYNC_LOCK_ID):
            return
        try:
            await run_sync(conn)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", SYNC_LOCK_ID)


# ---------------------------------------------------------------- alert matching

ALERT_MATCH_SQL = """
    SELECT a.alert_id, a.user_id, a.alert_frequency, u.email
    FROM trial_alerts a
    JOIN users u ON u.id = a.user_id AND u.is_active
    JOIN clinical_trials t ON t.trial_id = $1
    WHERE a.is_active
      AND (
        a.trial_id = t.trial_id
        OR (a.trial_id IS NULL
            AND (a.disease_area IS NULL OR t.disease_area ILIKE '%' || a.disease_area || '%'
                 OR a.disease_area ILIKE '%' || t.disease_area || '%')
            AND (a.phase IS NULL OR a.phase = t.phase)
            AND (a.location IS NULL OR t.countries ? a.location OR EXISTS (
                SELECT 1 FROM trial_sites s WHERE s.trial_id = t.trial_id
                AND (s.country ILIKE a.location OR s.city ILIKE a.location))))
      )
"""

PROFILE_MATCH_SQL = """
    SELECT u.id AS user_id
    FROM users u
    JOIN user_profiles p ON p.user_id = u.id
    JOIN clinical_trials t ON t.trial_id = $1
    WHERE u.is_active AND u.user_type IN ('patient', 'caregiver')
      AND (t.disease_area ILIKE '%' || NULLIF(p.condition, '') || '%'
           OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(p.interests, '[]'::jsonb)) i
                      WHERE t.disease_area ILIKE '%' || i || '%'))
"""


async def notify_matches(conn, trial_id) -> int:
    """Notify alert subscribers, then profile matches, about a new or newly recruiting trial. Returns users notified."""
    trial = await conn.fetchrow(
        "SELECT trial_id, title FROM clinical_trials WHERE trial_id = $1 AND status <> 'Draft'", trial_id
    )
    if not trial:
        return 0
    link = f"/trials/{trial_id}"
    already = {
        r["user_id"] for r in await conn.fetch(
            "SELECT user_id FROM notifications WHERE link = $1 AND type IN ('trial_alert', 'trial_match')", link
        )
    }
    service = NotificationService(conn)
    data = {"trial_id": str(trial_id), "trial_title": trial["title"], "reason": "it matches one of your trial alerts"}
    notified = 0

    for alert in await conn.fetch(ALERT_MATCH_SQL, trial_id):
        if alert["user_id"] in already:
            continue
        already.add(alert["user_id"])
        if await service.notify_user(str(alert["user_id"]), NotificationType.TRIAL_ALERT, data):
            notified += 1
            await conn.execute("UPDATE trial_alerts SET last_notified = NOW() WHERE alert_id = $1", alert["alert_id"])
            if alert["alert_frequency"] == "instant":
                # shortcut: daily/weekly alerts get the in-app notification only; email digests are not built yet
                try:
                    await EmailService.send_trial_alert(alert["email"], trial["title"], str(trial_id))
                except Exception as e:
                    logger.warning(f"Trial alert email to {alert['email']} failed: {e}")

    for match in await conn.fetch(PROFILE_MATCH_SQL, trial_id):
        if match["user_id"] in already:
            continue
        already.add(match["user_id"])
        if await service.notify_user(str(match["user_id"]), NotificationType.TRIAL_MATCH, data):
            notified += 1
    return notified
