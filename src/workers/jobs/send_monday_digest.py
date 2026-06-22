import logging

from src.api.dependencies import get_send_weekly_digest_use_case

logger = logging.getLogger(__name__)


async def send_monday_digest_job() -> None:
    logger.info("Starting weekly digest job")
    use_case = get_send_weekly_digest_use_case()
    sent = await use_case.execute()
    logger.info("Weekly digest job finished sent=%s", sent)
