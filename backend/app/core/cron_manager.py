import asyncio
import logging
import os
from typing import Callable, Coroutine, List
from app.db.postgres import PostgresDB
from app.models.user_model import UserModel
from app.services.verification_service import delete_licence

logger = logging.getLogger(__name__)

# Same folder that main.py serves at /static (relative to the backend folder)
UPLOADS_DIR = "uploads"

class CronJob:
    def __init__(self, name: str, func: Callable[[], Coroutine], interval_seconds: int):
        self.name = name
        self.func = func
        self.interval = interval_seconds
        self.task = None

class CronManager:
    def __init__(self):
        self.jobs: List[CronJob] = []
        self._running = False

    def add_job(self, name: str, func: Callable[[], Coroutine], interval_seconds: int):
        self.jobs.append(CronJob(name, func, interval_seconds))

    def start(self):
        if self._running:
            return
        self._running = True
        for job in self.jobs:
            job.task = asyncio.create_task(self._run_job(job))
        logger.info("CronManager started with %d jobs.", len(self.jobs))

    def stop(self):
        self._running = False
        for job in self.jobs:
            if job.task:
                job.task.cancel()
        logger.info("CronManager stopped.")

    async def _run_job(self, job: CronJob):
        while self._running:
            try:
                await job.func()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cron job '{job.name}': {e}", exc_info=True)
            await asyncio.sleep(job.interval)

# --- Cron Tasks ---

def _remove_uploaded_file(url: str | None):
    """Delete a file saved under uploads/ and served at /static/..."""
    if not url or not url.startswith("/static/"):
        return
    path = os.path.join(UPLOADS_DIR, url[len("/static/"):])
    if os.path.realpath(path).startswith(os.path.realpath(UPLOADS_DIR) + os.sep) and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError as e:
            logger.warning(f"Could not delete uploaded file {path}: {e}")


async def purge_deleted_accounts():
    """
    Anonymize user accounts scheduled for deletion that have passed their 1-week grace period.
    Each account is handled on its own, so one failure cannot block the others.
    """
    pool = PostgresDB.get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        user_model = UserModel(conn)
        anonymized = 0
        for user_id in await user_model.get_users_due_for_deletion():
            try:
                removed = await user_model.anonymize_user(user_id)
                _remove_uploaded_file(removed["avatar"])
                for document in removed["documents"]:
                    await delete_licence(document)
                anonymized += 1
            except Exception as e:
                logger.error(f"Cron [purge_deleted_accounts]: Could not anonymize user {user_id}: {e}", exc_info=True)
        if anonymized:
            logger.info(f"Cron [purge_deleted_accounts]: Anonymized {anonymized} scheduled account(s)")


async def lift_expired_suspensions():
    """
    Make accounts active again once their suspension end date has passed.
    (Login and every authenticated request also do this for the user concerned.)
    """
    pool = PostgresDB.get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        result = await UserModel(conn).lift_all_expired_suspensions()
        if result and result != "UPDATE 0":
            logger.info(f"Cron [lift_expired_suspensions]: Suspensions lifted: {result}")

SURVEY_REMINDER_LOCK_ID = 74210302  # one process at a time


async def survey_reminders():
    """
    Daily: expire overdue survey assignments, and remind patients once when an open
    assignment is due within 2 days.
    """
    from app.schemas.notification import NotificationType
    from app.services.notification_service import NotificationService

    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT pg_try_advisory_lock($1)", SURVEY_REMINDER_LOCK_ID):
            return
        try:
            await conn.execute(
                "UPDATE survey_assignments SET status = 'expired', updated_at = NOW() "
                "WHERE status IN ('pending', 'in_progress') AND due_date < NOW()"
            )
            due = await conn.fetch(
                """
                SELECT a.patient_user_id, s.survey_id, s.title, a.due_date
                FROM survey_assignments a
                JOIN surveys s ON s.survey_id = a.survey_id
                WHERE a.status IN ('pending', 'in_progress')
                  AND a.due_date BETWEEN NOW() AND NOW() + INTERVAL '2 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM notifications n
                      WHERE n.user_id = a.patient_user_id AND n.link = '/surveys/' || s.survey_id
                        AND n.title = 'Survey due soon'
                  )
                """
            )
            service = NotificationService(conn)
            for r in due:
                if await service._should_notify(str(r["patient_user_id"]), NotificationType.SURVEY_AVAILABLE):
                    await service.create_notification(
                        user_id=str(r["patient_user_id"]),
                        notif_type=NotificationType.SURVEY_AVAILABLE.value,
                        title="Survey due soon",
                        message=f'Please complete "{r["title"]}" by {r["due_date"]:%d %b %Y}.',
                        link=f"/surveys/{r['survey_id']}",
                    )
            if due:
                logger.info(f"Cron [survey_reminders]: sent {len(due)} reminders")
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", SURVEY_REMINDER_LOCK_ID)

# Singleton Cron Manager instance
cron_manager = CronManager()

# Register cron tasks here
cron_manager.add_job("purge_deleted_accounts", purge_deleted_accounts, interval_seconds=3600)
<<<<<<< HEAD
cron_manager.add_job("lift_expired_suspensions", lift_expired_suspensions, interval_seconds=3600)
=======

from app.services.trial_sync_service import scheduled_sync  # noqa: E402  (imported here to keep cron jobs in one place)
cron_manager.add_job("trial_sync", scheduled_sync, interval_seconds=24 * 3600)
cron_manager.add_job("survey_reminders", survey_reminders, interval_seconds=24 * 3600)
>>>>>>> origin/feature/phase2-ai-chatbot-trials-surveys
