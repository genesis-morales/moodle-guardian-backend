import logging
from datetime import UTC, datetime

from src.api.dependencies import (
    get_run_guardian_scan_use_case,
    get_scan_run_repository,
    get_user_repository,
)
from src.domain.entities.scan_run import ScanFailure, ScanRun

logger = logging.getLogger(__name__)


async def scan_all_users_job() -> None:
    logger.info("Starting scheduled scan for active users")

    user_repository = get_user_repository()
    run_guardian_scan_use_case = get_run_guardian_scan_use_case()

    users = await user_repository.list_active()
    logger.info("Loaded active users for scheduled scan count=%s", len(users))

    started_at = datetime.now(UTC)
    success_count = 0
    failure_count = 0
    failures: list[ScanFailure] = []

    for user in users:
        try:
            logger.info(
                "Running scheduled scan for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )
            await run_guardian_scan_use_case.execute(user.moodle_user_id)
            success_count += 1
        except Exception as exc:
            failure_count += 1
            failures.append(
                ScanFailure(
                    moodle_user_id=user.moodle_user_id,
                    error=f"{type(exc).__name__}: {exc}"[:500],
                )
            )
            logger.exception(
                "Scheduled scan failed for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )

    finished_at = datetime.now(UTC)

    # Persistimos el resumen de la corrida (observabilidad). Un fallo al guardar
    # el historial no debe tumbar el job; solo lo logueamos.
    try:
        await get_scan_run_repository().save(
            ScanRun(
                job_name="scan",
                started_at=started_at,
                finished_at=finished_at,
                total_users=len(users),
                success_count=success_count,
                failure_count=failure_count,
                failures=failures,
            )
        )
    except Exception:
        logger.exception("Failed to persist scan run summary")

    logger.info(
        "Scheduled scan finished total=%s success=%s failure=%s",
        len(users),
        success_count,
        failure_count,
    )
