import logging

from src.api.dependencies import get_run_guardian_scan_use_case, get_user_repository

logger = logging.getLogger(__name__)


async def scan_all_users_job() -> None:
    logger.info("Starting scheduled scan for active users")

    user_repository = get_user_repository()
    run_guardian_scan_use_case = get_run_guardian_scan_use_case()

    users = await user_repository.list_active()
    logger.info("Loaded active users for scheduled scan count=%s", len(users))

    success_count = 0
    failure_count = 0

    for user in users:
        try:
            logger.info(
                "Running scheduled scan for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )
            await run_guardian_scan_use_case.execute(user.moodle_user_id)
            success_count += 1
        except Exception:
            failure_count += 1
            logger.exception(
                "Scheduled scan failed for user_id=%s moodle_user_id=%s",
                user.id,
                user.moodle_user_id,
            )

    logger.info(
        "Scheduled scan finished total=%s success=%s failure=%s",
        len(users),
        success_count,
        failure_count,
    )