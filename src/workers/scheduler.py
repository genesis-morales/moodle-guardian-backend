import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import get_settings
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.workers.jobs.send_deadline_reminders import send_deadline_reminders_job
from src.workers.jobs.send_monday_digest import send_monday_digest_job

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
    tz = ZoneInfo(settings.timezone)
    # tz local en el scheduler para que los cron disparen en hora de CR aunque
    # el server esté en UTC.
    scheduler = AsyncIOScheduler(timezone=tz)

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

    # Recordatorio diario "faltan N días" a las reminder_hour (hora local).
    scheduler.add_job(
        send_deadline_reminders_job,
        trigger=CronTrigger(hour=settings.reminder_hour, minute=0, timezone=tz),
        id="send_deadline_reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # Digest semanal (p. ej. lunes 10:00 hora local).
    scheduler.add_job(
        send_monday_digest_job,
        trigger=CronTrigger(
            day_of_week=settings.digest_weekday,
            hour=settings.digest_hour,
            minute=0,
            timezone=tz,
        ),
        id="send_monday_digest",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    scheduler.add_listener(
        scheduler_listener,
        EVENT_JOB_EXECUTED
        | EVENT_JOB_ERROR
        | EVENT_JOB_MISSED
        | EVENT_JOB_MAX_INSTANCES,
    )

    logger.info(
        "Scheduler configured: scan=interval %sh (first_run=%s) | reminders=%02d:00 "
        "(faltan %sd) | digest=%s %02d:00 | tz=%s",
        settings.scheduler_interval_hours,
        "immediate" if settings.scheduler_run_immediately_on_start else "interval",
        settings.reminder_hour,
        settings.reminder_days_before,
        settings.digest_weekday,
        settings.digest_hour,
        settings.timezone,
    )
    return scheduler