import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.workers.jobs.scan_all_users import scan_all_users_job

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        scan_all_users_job,
        trigger="interval",
        hours=3,
        id="scan_all_users",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        next_run_time=datetime.now(),
    )

    logger.info("Scheduler configured: job=scan_all_users interval=3h first_run=immediate")
    return scheduler