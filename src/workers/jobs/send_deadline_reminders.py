import logging

from src.api.dependencies import get_send_deadline_reminders_use_case

logger = logging.getLogger(__name__)


async def send_deadline_reminders_job() -> None:
    logger.info("Starting deadline reminders job")
    use_case = get_send_deadline_reminders_use_case()
    sent = await use_case.execute()
    logger.info("Deadline reminders job finished sent=%s", sent)
