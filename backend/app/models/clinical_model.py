import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.base_model import DBModel


class ClinicalModel(DBModel):
    """
    Model for Clinical Trials domain.
    Handles trials, saves, alerts, and interest expressions.
    Strict adhesion to DB schema: clinical_trials, trial_sites, trial_saves, trial_alerts.
    """

    # ------------------------------------------------------------------
    # 1. SEARCH & LIST TRIALS
    # ------------------------------------------------------------------
    async def search_trials(
        self,
        *,
        keyword: Optional[str] = None,
        disease_areas: Optional[List[str]] = None,
        phases: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        location: Optional[str] = None,
        sponsor: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "relevance",
        user_id: Optional[str] = None,
        include_drafts: bool = False,
        match_conditions: Optional[List[str]] = None,
        match_country: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = []
        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        keyword_val = keyword.strip() if keyword and keyword.strip() else None
        where_conditions = []

        if keyword_val:
            kw_ph = add_param(keyword_val)
            where_conditions.append(
                f"to_tsvector('english', t.title || ' ' || COALESCE(t.summary, '')) @@ plainto_tsquery('english', {kw_ph})"
            )

        if disease_areas:
            da_ph = add_param(disease_areas)
            where_conditions.append(f"t.disease_area = ANY({da_ph})")

        if phases:
            ph_ph = add_param(phases)
            where_conditions.append(f"t.phase = ANY({ph_ph})")

        if statuses:
            st_ph = add_param(statuses)
            where_conditions.append(f"t.status = ANY({st_ph})")

        if location:
            loc_val = f"%{location}%"
            loc_ph = add_param(loc_val)
            where_conditions.append(
                f"""EXISTS (
                    SELECT 1 FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                    AND (ts.country ILIKE {loc_ph} OR ts.city ILIKE {loc_ph})
                )"""
            )

        if sponsor:
            sp_ph = add_param(f"%{sponsor}%")
            where_conditions.append(f"t.sponsor ILIKE {sp_ph}")

        if not include_drafts:
            where_conditions.append("t.status <> 'Draft'")

        # "Eligible for me": trial condition matches the patient's condition/interests,
        # and the trial runs in the patient's country.
        if match_conditions:
            mc_ph = add_param([f"%{c}%" for c in match_conditions])
            where_conditions.append(f"t.disease_area ILIKE ANY({mc_ph})")
        if match_country:
            ctry_ph = add_param(match_country)
            where_conditions.append(
                f"""(t.countries ? {ctry_ph} OR EXISTS (
                    SELECT 1 FROM trial_sites ts WHERE ts.trial_id = t.trial_id AND ts.country ILIKE {ctry_ph}
                ))"""
            )

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        where_params = list(params)

        if user_id:
            user_ph = add_param(user_id)
            is_saved_expr = f"""
                EXISTS (
                    SELECT 1 FROM trial_saves ts 
                    WHERE ts.trial_id = t.trial_id AND ts.user_id = {user_ph}
                )
            """
        else:
            is_saved_expr = "false"

        if keyword_val:
            rank_expr = f"""
                ts_rank(
                    to_tsvector('english', t.title || ' ' || COALESCE(t.summary, '')),
                    plainto_tsquery('english', ${params.index(keyword_val) + 1})
                )
            """
            rank_col = f"{rank_expr} AS rank"
        else:
            rank_col = "0::float4 AS rank"

        if sort_by == "relevance" and keyword_val:
            order_by = "ORDER BY rank DESC, t.created_at DESC"
        elif sort_by == "newest":
            order_by = "ORDER BY t.created_at DESC"
        elif sort_by == "enrollment":
            order_by = "ORDER BY t.enrollment DESC NULLS LAST"
        else:
            order_by = "ORDER BY t.created_at DESC"

        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        location_agg = """
            (
                SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                FROM trial_sites ts
                WHERE ts.trial_id = t.trial_id
            ) AS location
        """

        # Aliasing trial_id AS id
        query = f"""
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                t.disease_area,
                ARRAY(SELECT jsonb_array_elements_text(t.countries)) AS countries,
                {location_agg},
                t.enrollment AS enrollment_count,
                t.max_enrollment,
                {is_saved_expr} AS is_saved,
                {rank_col}
            FROM clinical_trials t
            {where_clause}
            {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """

        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        # Same filters as the list query, so the total can never disagree with the items.
        total = await self.conn.fetchval(
            f"SELECT COUNT(*) FROM clinical_trials t {where_clause}", *where_params
        ) or 0

        pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    # ------------------------------------------------------------------
    # 2. GET TRIAL BY ID
    # ------------------------------------------------------------------
    async def get_trial_by_id(
        self, trial_id: str, user_id: Optional[str] = None, include_drafts: bool = False
    ) -> Optional[Dict[str, Any]]:
        params = [trial_id]
        if user_id:
            params.append(user_id)
            saved_expr = "EXISTS (SELECT 1 FROM trial_saves ts WHERE ts.trial_id = t.trial_id AND ts.user_id = $2)"
        else:
            saved_expr = "false"

        # Aliasing trial_id AS id
        query = f"""
            SELECT
                t.trial_id AS id,
                t.nct_id,
                t.title,
                t.summary,
                t.disease_area,
                t.phase,
                t.status,
                t.sponsor,
                t.countries, 
                t.eligibility_criteria,
                t.eligibility_rules,
                t.enrollment AS enrollment_count,
                t.max_enrollment,
                t.start_date,
                t.estimated_completion,
                t.contact,
                t.metadata,
                t.created_at,
                t.last_updated AS updated_at,
                {saved_expr} AS is_saved,
                COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object(
                        'site_id', ts.site_id,
                        'site_name', ts.site_name,
                        'country', ts.country,
                        'city', ts.city,
                        'address', ts.address,
                        'contact_email', ts.contact_email,
                        'contact_phone', ts.contact_phone,
                        'is_recruiting', ts.is_recruiting
                    ))
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id),
                    '[]'::jsonb
                ) AS sites,
                (
                    SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                ) AS location
            FROM clinical_trials t
            WHERE t.trial_id = $1 {"" if include_drafts else "AND t.status <> 'Draft'"}
        """
        record = await self.conn.fetchrow(query, *params)
        if not record:
            return None
        
        data = dict(record)
        
        # Deserialize JSON fields if they are strings
        for field in ['sites', 'countries', 'metadata', 'eligibility_rules', 'objectives', 'safety_info']:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    # Fallback to empty default or raw
                    if field == 'sites': data[field] = []
                    elif field == 'countries': data[field] = []
                    elif field == 'metadata': data[field] = {}
        
        # Ensure lists are lists
        if data.get('countries') is None: data['countries'] = []
        if data.get('sites') is None: data['sites'] = []
        
        return data

    # ------------------------------------------------------------------
    # 3. SAVE / UNSAVE
    # ------------------------------------------------------------------
    async def save_trial(self, user_id: str, trial_id: str, notes: Optional[str] = None) -> bool:
        query = """
            INSERT INTO trial_saves (user_id, trial_id, notes, saved_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, trial_id) DO NOTHING
            RETURNING user_id
        """
        val = await self.conn.fetchval(query, user_id, trial_id, notes)
        return bool(val)

    async def unsave_trial(self, user_id: str, trial_id: str) -> bool:
        query = """
            DELETE FROM trial_saves
            WHERE user_id = $1 AND trial_id = $2
            RETURNING 1
        """
        val = await self.conn.fetchval(query, user_id, trial_id)
        return bool(val)

    async def get_saved_trials(self, user_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                t.enrollment AS enrollment_count,
                (
                    SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                ) AS location,
                tsave.saved_at
            FROM trial_saves tsave
            JOIN clinical_trials t ON tsave.trial_id = t.trial_id
            WHERE tsave.user_id = $1
            ORDER BY tsave.saved_at DESC
        """
        records = await self.conn.fetch(query, user_id)
        return self._records_to_list(records)

    # ------------------------------------------------------------------
    # 4. INTEREST
    # ------------------------------------------------------------------
    async def express_interest(self, user_id: str, trial_id: str, message: Optional[str]) -> Dict[str, Any]:
        await self.conn.execute(
            """
            INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, metadata)
            VALUES ($1, 'express_interest', 'trial', $2, $3)
            """,
            user_id, trial_id, json.dumps({"message_length": len(message) if message else 0})
        )
        
        return {
            "trial_id": trial_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc)
        }

    # ------------------------------------------------------------------
    # 5. ALERTS
    # ------------------------------------------------------------------
    async def create_trial_alert(
        self,
        user_id: str,
        *,
        disease_area: Optional[str] = None,
        location: Optional[str] = None,
        phase: Optional[str] = None,
        filter_criteria: Optional[Dict] = None,
        alert_frequency: str = "weekly",
        trial_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # JSON serialize filter_criteria
        query = """
            INSERT INTO trial_alerts (
                user_id, trial_id, disease_area, location, phase,
                filter_criteria, alert_frequency, is_active, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW(), NOW())
            RETURNING alert_id, created_at, updated_at, is_active, 
                      disease_area, location, phase, filter_criteria, alert_frequency
        """
        row = await self.conn.fetchrow(
            query,
            user_id,
            trial_id,
            disease_area,
            location,
            phase,
            json.dumps(filter_criteria or {}),
            alert_frequency,
        )
        data = self._record_to_dict(row)
        if isinstance(data.get("filter_criteria"), str):
            try:
                data["filter_criteria"] = json.loads(data["filter_criteria"])
            except:
                data["filter_criteria"] = {}
        return data

    async def get_my_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT
                alert_id,
                disease_area,
                location,
                phase,
                filter_criteria,
                alert_frequency,
                is_active,
                created_at,
                updated_at
            FROM trial_alerts
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        rows = await self.conn.fetch(query, user_id)
        # Deserialize JSONB
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("filter_criteria"), str):
                 try:
                     d["filter_criteria"] = json.loads(d["filter_criteria"])
                 except:
                     pass
            results.append(d)
        return results

    async def delete_trial_alert(self, alert_id: str, user_id: str) -> bool:
        query = "DELETE FROM trial_alerts WHERE alert_id = $1 AND user_id = $2 RETURNING 1"
        val = await self.conn.fetchval(query, alert_id, user_id)
        return bool(val)
        
    async def update_trial_alert(self, alert_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not updates:
            return None
            
        set_parts = []
        vals = [alert_id, user_id]
        
        for k, v in updates.items():
            if k == 'filter_criteria':
                vals.append(json.dumps(v))
            else:
                vals.append(v)
            set_parts.append(f"{k} = ${len(vals)}")
            
        set_parts.append("updated_at = NOW()")
        
        query = f"""
            UPDATE trial_alerts
            SET {", ".join(set_parts)}
            WHERE alert_id = $1 AND user_id = $2
            RETURNING alert_id, disease_area, location, phase, 
                      filter_criteria, alert_frequency, is_active, created_at, updated_at
        """
        row = await self.conn.fetchrow(query, *vals)
        if not row:
            return None
        data = self._record_to_dict(row)
        if isinstance(data.get("filter_criteria"), str):
            try:
                data["filter_criteria"] = json.loads(data["filter_criteria"])
            except:
                pass
        return data

    # ------------------------------------------------------------------
    # 6. OBSERVATIONS
    # ------------------------------------------------------------------
    async def create_observation(self, trial_id: str, doctor_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        severity = data.get('severity_level')
        flagged = True if severity == 'critical' else False
        
        query = """
            INSERT INTO clinical_observations (
                trial_id, doctor_id, summary, feedback_data, 
                severity_level, flagged, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING observation_id, trial_id, doctor_id, summary, 
                      feedback_data, severity_level, flagged, created_at
        """
        row = await self.conn.fetchrow(
            query,
            trial_id,
            doctor_id,
            data['summary'],
            json.dumps(data.get('feedback_data', {})),
            severity,
            flagged
        )
        result = dict(row)
        if isinstance(result['feedback_data'], str):
             result['feedback_data'] = json.loads(result['feedback_data'])
        return result

    async def get_observations(self, trial_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM clinical_observations 
            WHERE trial_id = $1 
            ORDER BY created_at DESC
        """
        rows = await self.conn.fetch(query, trial_id)
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get('feedback_data'), str):
                try: d['feedback_data'] = json.loads(d['feedback_data'])
                except: pass
            results.append(d)
        return results

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------
    # Allowed status changes. Completed and Terminated are final.
    STATUS_TRANSITIONS = {
        "Draft": {"Not yet recruiting", "Recruiting"},
        "Not yet recruiting": {"Recruiting", "Suspended", "Terminated"},
        "Recruiting": {"Active", "Completed", "Suspended", "Terminated"},
        "Active": {"Completed", "Suspended", "Terminated"},
        "Suspended": {"Recruiting", "Active", "Terminated"},
        "Completed": set(),
        "Terminated": set(),
    }

    async def get_trial_manager(self, trial_id) -> Optional[Any]:
        return await self.conn.fetchval("SELECT managed_by_id FROM clinical_trials WHERE trial_id = $1", trial_id)

    async def set_trial_manager(self, trial_id, hcp_user_id) -> bool:
        result = await self.conn.execute(
            "UPDATE clinical_trials SET managed_by_id = $2, last_updated = NOW() WHERE trial_id = $1", trial_id, hcp_user_id)
        return result.endswith(" 1")

    async def list_managed_trials(self, hcp_user_id) -> List[Dict[str, Any]]:
        rows = await self.conn.fetch(
            """
            SELECT t.trial_id, t.title, t.status, t.phase, t.disease_area, t.enrollment, t.max_enrollment,
                   count(r.id) AS referrals, count(r.id) FILTER (WHERE r.status = 'enrolled') AS enrolled
            FROM clinical_trials t
            LEFT JOIN trial_referrals r ON r.trial_id = t.trial_id
            WHERE t.managed_by_id = $1
            GROUP BY t.trial_id
            ORDER BY t.last_updated DESC NULLS LAST
            """,
            hcp_user_id,
        )
        trials = self._records_to_list(rows)
        for t in trials:
            t["next_statuses"] = sorted(self.STATUS_TRANSITIONS.get(t["status"], set()))
        return trials

    async def recent_observations(self, hcp_user_id, limit: int = 20) -> List[Dict[str, Any]]:
        """Observations the doctor wrote, plus any on trials they manage."""
        rows = await self.conn.fetch(
            """
            SELECT o.observation_id, o.trial_id, o.doctor_id, o.summary, o.feedback_data, o.severity_level,
                   o.flagged, o.created_at, t.title AS trial_title, d.display_name AS doctor_name
            FROM clinical_observations o
            JOIN clinical_trials t ON t.trial_id = o.trial_id
            LEFT JOIN users d ON d.id = o.doctor_id
            WHERE o.doctor_id = $1 OR t.managed_by_id = $1
            ORDER BY o.created_at DESC
            LIMIT $2
            """,
            hcp_user_id, limit,
        )
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("feedback_data"), str):
                d["feedback_data"] = json.loads(d["feedback_data"] or "{}")
            results.append(d)
        return results

    async def get_trial_status(self, trial_id: str) -> Optional[str]:
        return await self.conn.fetchval("SELECT status FROM clinical_trials WHERE trial_id = $1", trial_id)

    async def change_status(self, trial_id: str, from_status: str, to_status: str) -> bool:
        """Compare-and-set, so two admins changing the same trial at once cannot skip a step."""
        row = await self.conn.fetchrow(
            "UPDATE clinical_trials SET status = $3, last_updated = NOW() "
            "WHERE trial_id = $1 AND status = $2 RETURNING trial_id",
            trial_id, from_status, to_status,
        )
        return row is not None

    async def get_eligibility_rules(self, trial_id: str) -> Optional[Dict[str, Any]]:
        rules = await self.conn.fetchval(
            "SELECT eligibility_rules FROM clinical_trials WHERE trial_id = $1 AND status <> 'Draft'", trial_id
        )
        if rules is None:
            return None
        return json.loads(rules) if isinstance(rules, str) else rules

    async def get_match_profile(self, user_id: str) -> Dict[str, Any]:
        """Condition, interests and country used by the 'eligible for me' search filter."""
        row = await self.conn.fetchrow(
            """
            SELECT u.country, p.condition, p.interests
            FROM users u LEFT JOIN user_profiles p ON p.user_id = u.id
            WHERE u.id = $1
            """,
            user_id,
        )
        if not row:
            return {"conditions": [], "country": None}
        interests = row["interests"]
        if isinstance(interests, str):
            interests = json.loads(interests)
        conditions = [c for c in [row["condition"], *(interests or [])] if isinstance(c, str) and c.strip()]
        return {"conditions": conditions, "country": row["country"]}

    # ------------------------------------------------------------------
    # REFERRALS
    # ------------------------------------------------------------------
    REFERRAL_COLUMNS = """
        r.id, r.trial_id, t.title AS trial_title, t.status AS trial_status,
        r.hcp_user_id, hcp.display_name AS hcp_name,
        r.patient_user_id, COALESCE(pat.display_name, r.patient_email) AS patient_name,
        r.patient_email, r.clinical_notes, r.status, r.created_at, r.updated_at
    """
    REFERRAL_JOINS = """
        FROM trial_referrals r
        JOIN clinical_trials t ON t.trial_id = r.trial_id
        LEFT JOIN users hcp ON hcp.id = r.hcp_user_id
        LEFT JOIN users pat ON pat.id = r.patient_user_id
    """

    async def create_referral(self, trial_id, hcp_user_id, patient_user_id, patient_email, clinical_notes):
        referral_id = await self.conn.fetchval(
            """
            INSERT INTO trial_referrals (trial_id, hcp_user_id, patient_user_id, patient_email, clinical_notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            trial_id, hcp_user_id, patient_user_id, patient_email, clinical_notes,
        )
        return await self.get_referral(referral_id)

    async def get_referral(self, referral_id) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(f"SELECT {self.REFERRAL_COLUMNS} {self.REFERRAL_JOINS} WHERE r.id = $1", referral_id)
        return dict(row) if row else None

    async def list_sent_referrals(self, hcp_user_id) -> List[Dict[str, Any]]:
        rows = await self.conn.fetch(
            f"SELECT {self.REFERRAL_COLUMNS} {self.REFERRAL_JOINS} WHERE r.hcp_user_id = $1 ORDER BY r.created_at DESC",
            hcp_user_id,
        )
        return self._records_to_list(rows)

    async def list_received_referrals(self, user_id, email: str) -> List[Dict[str, Any]]:
        """Claims referrals sent to this email before the patient had an account, and marks new ones as viewed."""
        async with self.conn.transaction():
            await self.conn.execute(
                "UPDATE trial_referrals SET patient_user_id = $1, updated_at = NOW() "
                "WHERE patient_user_id IS NULL AND lower(patient_email) = lower($2)",
                user_id, email,
            )
            await self.conn.execute(
                "UPDATE trial_referrals SET status = 'viewed', updated_at = NOW() "
                "WHERE patient_user_id = $1 AND status = 'sent'",
                user_id,
            )
            rows = await self.conn.fetch(
                f"SELECT {self.REFERRAL_COLUMNS} {self.REFERRAL_JOINS} WHERE r.patient_user_id = $1 ORDER BY r.created_at DESC",
                user_id,
            )
        return self._records_to_list(rows)

    async def respond_to_referral(self, referral_id, user_id, email: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Only the referred patient can respond, and only while the referral is still open."""
        row = await self.conn.fetchrow(
            """
            UPDATE trial_referrals
            SET status = $4, patient_user_id = $2, updated_at = NOW()
            WHERE id = $1
              AND (patient_user_id = $2 OR (patient_user_id IS NULL AND lower(patient_email) = lower($3)))
              AND status IN ('sent', 'viewed')
            RETURNING id
            """,
            referral_id, user_id, email, new_status,
        )
        return await self.get_referral(row["id"]) if row else None

    async def self_enroll(self, trial_id, user_id, email: str) -> Dict[str, Any]:
        """
        Start enrolment without a doctor: returns a consent_pending referral for the consent form.
        An open doctor referral for the same trial is reused (accepting it), so a patient never has two.
        """
        async with self.conn.transaction():
            existing = await self.conn.fetchrow(
                "SELECT id, status FROM trial_referrals WHERE trial_id = $1 "
                "AND (patient_user_id = $2 OR lower(patient_email) = lower($3)) "
                "AND status NOT IN ('declined', 'ineligible') ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
                trial_id, user_id, email,
            )
            if existing and existing["status"] == "enrolled":
                raise ValueError("You are already enrolled in this trial")
            if existing:
                await self.conn.execute(
                    "UPDATE trial_referrals SET status = 'consent_pending', patient_user_id = $2, updated_at = NOW() WHERE id = $1",
                    existing["id"], user_id,
                )
                referral_id = existing["id"]
            else:
                referral_id = await self.conn.fetchval(
                    "INSERT INTO trial_referrals (trial_id, hcp_user_id, patient_user_id, patient_email, status) "
                    "VALUES ($1, NULL, $2, $3, 'consent_pending') RETURNING id",
                    trial_id, user_id, email,
                )
        return await self.get_referral(referral_id)

    async def referral_exists_for_patient(self, referral_id, user_id, email: str) -> bool:
        return bool(await self.conn.fetchval(
            "SELECT 1 FROM trial_referrals WHERE id = $1 "
            "AND (patient_user_id = $2 OR (patient_user_id IS NULL AND lower(patient_email) = lower($3)))",
            referral_id, user_id, email,
        ))
