import logging
from datetime import datetime

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.settings import get_settings
from src.workers.jobs.scan_all_users import scan_all_users_job

logger = logging.getLogger(__name__)


def scheduler_listener(event) -> None:
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(
            "Scheduler event: job executed successfully job_id=%s scheduled_run_time=%s",
            event.job_id,
            event.scheduled_run_time,
        )
    elif event.code == EVENT_JOB_ERROR:
        logger.error(
            "Scheduler event: job failed job_id=%s scheduled_run_time=%s exception=%s",
            event.job_id,
            event.scheduled_run_time,
            event.exception,
        )
    elif event.code == EVENT_JOB_MISSED:
        logger.warning(
            "Scheduler event: job missed job_id=%s scheduled_run_time=%s",
            event.job_id,
            event.scheduled_run_time,
        )
    elif event.code == EVENT_JOB_MAX_INSTANCES:
        logger.warning(
            "Scheduler event: max instances reached job_id=%s scheduled_run_times=%s",
            event.job_id,
            event.scheduled_run_times,
        )


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        scan_all_users_job,
        trigger="interval",
        hours=settings.scheduler_interval_hours,
        #minutes=1,
        id="scan_all_users",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        next_run_time=(
            datetime.now() if settings.scheduler_run_immediately_on_start else None
        ),
    )

    scheduler.add_listener(
        scheduler_listener,
        EVENT_JOB_EXECUTED
        | EVENT_JOB_ERROR
        | EVENT_JOB_MISSED
        | EVENT_JOB_MAX_INSTANCES,
    )

    logger.info(
        "Scheduler configured: job=scan_all_users interval=%sh first_run=%s",
        settings.scheduler_interval_hours,
        "immediate" if settings.scheduler_run_immediately_on_start else "interval",
    )
    return scheduler