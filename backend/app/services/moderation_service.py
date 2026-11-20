"""
Content moderation: the automatic filter and moderator decisions.

The filter scores text with the editable rules in app/core/moderation_rules.py.
Moderator decisions change the content's status, can warn, suspend or ban its author,
close every open report on that content, and are recorded in moderation_actions,
the audit log and a notification to the author.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core import moderation_rules as rules
from app.models.moderation_model import ModerationModel, OPEN_REPORT_STATUSES
from app.schemas.notification import NotificationType
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# ======================================================================
# AUTOMATIC FILTER
# ======================================================================

_COMPILED = {
    category: [(re.compile(rule.pattern, re.IGNORECASE), rule) for rule in category_rules]
    for category, category_rules in rules.RULES.items()
}
_LINK = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
# The same character many times in a row, ignoring Markdown lines like "----------" and "......"
_REPEATED = re.compile(r"([^\s\-=_*#~.])\1{%d,}" % (rules.REPEATED_CHARACTERS - 1))


@dataclass(frozen=True)
class FilterMatch:
    category: str
    label: str
    weight: float


@dataclass
class FilterResult:
    score: float = 0.0
    matches: List[FilterMatch] = field(default_factory=list)

    @property
    def held(self) -> bool:
        """Kept out of public view until a moderator approves it."""
        return self.score >= rules.HOLD_THRESHOLD

    @property
    def needs_review(self) -> bool:
        """Sent to the moderation queue (held content always is)."""
        return self.score >= rules.FLAG_THRESHOLD

    @property
    def category(self) -> Optional[str]:
        """The report reason: self-harm first, otherwise the category with the most weight."""
        if not self.matches:
            return None
        if any(m.category == "self_harm" for m in self.matches):
            return "self_harm"
        totals: Dict[str, float] = {}
        for m in self.matches:
            totals[m.category] = totals.get(m.category, 0) + m.weight
        return max(totals, key=totals.get)

    @property
    def priority(self) -> str:
        if any(m.category == "self_harm" for m in self.matches):
            return "critical"
        return "high" if self.held else "normal"

    @property
    def reason(self) -> Optional[str]:
        if not self.matches:
            return None
        labels = sorted({m.label for m in self.matches})
        return ("Automatic filter: " + "; ".join(labels))[:255]


def score_content(*texts: Optional[str]) -> FilterResult:
    """Score a post's title and content (or a comment) with the moderation rules."""
    text = "\n".join(t for t in texts if t)
    if not text.strip():
        return FilterResult()

    matches: List[FilterMatch] = []
    for category, compiled in _COMPILED.items():
        for regex, rule in compiled:
            if regex.search(text):
                matches.append(FilterMatch(category, rule.label, rule.weight))

    links = len(_LINK.findall(text))
    if links >= rules.LINKS_TO_HOLD:
        matches.append(FilterMatch("spam", f"{links} links", rules.LINKS_HOLD_WEIGHT))
    elif links >= rules.LINKS_TO_FLAG:
        matches.append(FilterMatch("spam", f"{links} links", rules.LINKS_FLAG_WEIGHT))

    letters = [c for c in text if c.isalpha()]
    if len(letters) >= rules.SHOUTING_MIN_LETTERS:
        if sum(c.isupper() for c in letters) / len(letters) >= rules.SHOUTING_RATIO:
            matches.append(FilterMatch("spam", "written in capitals", rules.SHOUTING_WEIGHT))

    if _REPEATED.search(text):
        matches.append(FilterMatch("spam", "repeated characters", rules.REPEATED_WEIGHT))

    totals: Dict[str, float] = {}
    for m in matches:
        totals[m.category] = totals.get(m.category, 0) + m.weight
    score = sum(
        min(total, rules.CATEGORY_MAX_WEIGHT.get(category, 1.0))
        for category, total in totals.items()
    )
    return FilterResult(score=round(min(score, 1.0), 2), matches=matches)


# ======================================================================
# MODERATOR DECISIONS
# ======================================================================

USER_ACTIONS = {"warn_user", "suspend_user", "ban_user"}
CONTENT_STATUS_FOR_ACTION = {
    "approve_content": "approved",
    "hide_content": "hidden",
    "delete_content": "removed",
}
VISIBLE = "approved"


class ModerationError(Exception):
    """A decision that can't be applied. status_code is the HTTP status to return."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ModerationService:
    def __init__(self, conn):
        self.conn = conn
        self.model = ModerationModel(conn)

    async def queue(self, **filters) -> Dict[str, Any]:
        return await self.model.list_queue(**filters)

    async def decide(
        self,
        report_id: str,
        moderator: Dict[str, Any],
        action: str,
        reason: Optional[str] = None,
        duration_hours: Optional[int] = None,
        remove_content: bool = False,
    ) -> Dict[str, Any]:
        moderator_id = str(moderator["id"])

        async with self.conn.transaction():
            report = await self.model.get_report_for_update(report_id)
            if not report:
                raise ModerationError(404, "NOT_FOUND", "Report not found")
            if report["status"] not in OPEN_REPORT_STATUSES:
                raise ModerationError(409, "ALREADY_DECIDED", "This report has already been decided")

            target = await self.model.get_target(report["target_type"], str(report["target_id"]))
            content_target = target is not None and report["target_type"] in ("post", "comment")
            if report["target_type"] == "user":
                author_id = str(report["target_id"])
            else:
                author_id = str(target["author_id"]) if target and target.get("author_id") else None

            if action in CONTENT_STATUS_FOR_ACTION and action != "approve_content" and not content_target:
                raise ModerationError(400, "NO_CONTENT", "This report has no post or comment to act on")
            if remove_content and not content_target:
                raise ModerationError(400, "NO_CONTENT", "This report has no post or comment to remove")

            author = await self.model.get_user(author_id) if author_id else None
            if action in USER_ACTIONS:
                if not author or author.get("status") == "deleted":
                    raise ModerationError(400, "NO_AUTHOR", "The author's account no longer exists")
                if author_id == moderator_id:
                    raise ModerationError(400, "OWN_ACCOUNT", "You can't take action against your own account")
                if author.get("user_type") == "admin":
                    raise ModerationError(400, "ADMIN_ACCOUNT", "Admin accounts can't be warned, suspended or banned")

            # 1. The content
            old_status = target["moderation_status"] if content_target else None
            new_status = old_status
            if content_target:
                if action in CONTENT_STATUS_FOR_ACTION:
                    new_status = CONTENT_STATUS_FOR_ACTION[action]
                elif remove_content:
                    new_status = "removed"
                if new_status != old_status:
                    await self.model.set_content_status(
                        report["target_type"], str(report["target_id"]), new_status,
                        clear_flag=(new_status == VISIBLE),
                    )
                    if report["target_type"] == "comment":
                        await self.model.recount_replies(str(target["post_id"]))

            # 2. The author
            suspended_until = None
            if action == "suspend_user":
                suspended_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
                await self.model.suspend_user(author_id, suspended_until, reason)
            elif action == "ban_user":
                await self.model.suspend_user(author_id, None, reason)

            # 3. The reports: this one and every other open report on the same content
            report_status = "dismissed" if action == "approve_content" else "actioned"
            closed = await self.model.close_reports(
                report, report_status, moderator_id, action, reason,
                whole_target=content_target or report["target_type"] == "user",
            )

            # 4. The record
            await self.model.record_action(
                moderator_id=moderator_id,
                target_user_id=author_id,
                report_id=str(report["report_id"]),
                target_type=report["target_type"],
                target_id=str(report["target_id"]),
                action_type=action,
                reason=reason,
                duration_hours=duration_hours if action == "suspend_user" else None,
            )
            if remove_content and action in USER_ACTIONS and new_status != old_status:
                await self.model.record_action(
                    moderator_id=moderator_id,
                    target_user_id=author_id,
                    report_id=str(report["report_id"]),
                    target_type=report["target_type"],
                    target_id=str(report["target_id"]),
                    action_type="delete_content",
                    reason=reason,
                )

            await AuditService(self.conn).log_action(
                user_id=moderator_id,
                action=f"moderation.{action}",
                target_type=report["target_type"],
                target_id=str(report["target_id"]),
                metadata={
                    "report_id": str(report["report_id"]),
                    "author_id": author_id,
                    "reason": reason,
                    "duration_hours": duration_hours if action == "suspend_user" else None,
                    "content_status": {"before": old_status, "after": new_status},
                    "reports_closed": closed,
                },
            )

        # 5. Tell the author (after the decision is saved; a failed notification doesn't undo it)
        if author_id and author and author.get("status") != "deleted":
            message = self._author_message(
                action, report["target_type"], reason, old_status, new_status, suspended_until
            )
            if message:
                link = None
                if content_target and new_status == VISIBLE:
                    link = f"/community/{target['community_id']}/posts/{target['post_id']}"
                try:
                    await NotificationService(self.conn).notify_user(
                        user_id=author_id,
                        notif_type=NotificationType.MODERATION_ACTION,
                        data={**message, "link": link},
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Could not notify user {author_id} about moderation: {e}")

        return {
            "report_id": str(report["report_id"]),
            "action": action,
            "report_status": report_status,
            "reports_closed": closed,
            "content_status": new_status,
            "author_status": "suspended" if action in ("suspend_user", "ban_user") else (author or {}).get("status"),
            "suspended_until": suspended_until,
        }

    @staticmethod
    def _author_message(
        action: str,
        target_type: str,
        reason: Optional[str],
        old_status: Optional[str],
        new_status: Optional[str],
        suspended_until: Optional[datetime],
    ) -> Optional[Dict[str, str]]:
        """What the author is told. Nothing when a report about visible content is dismissed."""
        thing = "comment" if target_type == "comment" else "post"
        because = f" Reason: {reason}" if reason else ""

        if action == "approve_content":
            if old_status and old_status != VISIBLE and new_status == VISIBLE:
                return {
                    "title": f"Your {thing} is now visible",
                    "message": f"A moderator reviewed your {thing} and it is now visible to everyone.",
                }
            return None
        if action == "hide_content":
            return {
                "title": f"Your {thing} was hidden",
                "message": f"A moderator hid your {thing} from the community.{because}",
            }
        if action == "delete_content":
            return {
                "title": f"Your {thing} was removed",
                "message": f"A moderator removed your {thing} for breaking the community guidelines.{because}",
            }

        removed = f" Your {thing} was also removed." if new_status != old_status and new_status == "removed" else ""
        if action == "warn_user":
            return {
                "title": "Warning from the moderators",
                "message": f"Please follow the community guidelines.{because}{removed}",
            }
        if action == "suspend_user":
            until = suspended_until.strftime("%d %b %Y, %H:%M UTC") if suspended_until else ""
            return {
                "title": "Your account was suspended",
                "message": f"Your account is suspended until {until}.{because}{removed}",
            }
        if action == "ban_user":
            return {
                "title": "Your account was banned",
                "message": f"Your account was permanently suspended.{because}{removed}",
            }
        return None
