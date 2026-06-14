import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.settings import get_settings
from src.workers.jobs.scan_all_users import scan_all_users_job

logger = logging.getLogger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        scan_all_users_job,
        trigger="interval",
        hours=settings.scheduler_interval_hours,
        id="scan_all_users",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        next_run_time=(
            datetime.now() if settings.scheduler_run_immediately_on_start else None
        ),
    )

    logger.info(
        "Scheduler configured: job=scan_all_users interval=%sh first_run=%s",
        settings.scheduler_interval_hours,
        "immediate" if settings.scheduler_run_immediately_on_start else "interval",
    )
    return scheduler