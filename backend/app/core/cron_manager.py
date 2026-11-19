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

# Singleton Cron Manager instance
cron_manager = CronManager()

# Register cron tasks here
cron_manager.add_job("purge_deleted_accounts", purge_deleted_accounts, interval_seconds=3600)
cron_manager.add_job("lift_expired_suspensions", lift_expired_suspensions, interval_seconds=3600)
