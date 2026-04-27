import asyncio
import logging
from typing import Callable, Coroutine, List
from app.db.postgres import PostgresDB

logger = logging.getLogger(__name__)

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

async def purge_deleted_accounts():
    """
    Purge user accounts scheduled for deletion that have passed their 1-week grace period.
    """
    pool = PostgresDB.get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        query = "DELETE FROM users WHERE deletion_scheduled_at <= NOW()"
        deleted_count = await conn.execute(query)
        if deleted_count and deleted_count != "DELETE 0":
            logger.info(f"Cron [purge_deleted_accounts]: Successfully purged scheduled accounts: {deleted_count}")

# Singleton Cron Manager instance
cron_manager = CronManager()

# Register cron tasks here
cron_manager.add_job("purge_deleted_accounts", purge_deleted_accounts, interval_seconds=3600)
