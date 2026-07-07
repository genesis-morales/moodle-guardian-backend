import logging

from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User
from src.domain.ports.notifier_gateway import NotifierGateway

logger = logging.getLogger(__name__)


class NotifyUserChangesUseCase:
    def __init__(
        self,
        notifier: NotifierGateway,
        message_builder: NotificationMessageBuilder,
    ) -> None:
        self.notifier = notifier
        self.message_builder = message_builder

    async def execute(
        self, user: User, diff: DiffResult, site_label: str | None = None
    ) -> bool:
        logger.info("Evaluating notification for user_id=%s", user.id)

        if not diff.has_changes:
            logger.info("Notification skipped: no changes for user_id=%s", user.id)
            return False

        if not user.telegram_chat_id:
            logger.info("Notification skipped: missing telegram_chat_id for user_id=%s", user.id)
            return False

        logger.info("Building notification message for user_id=%s", user.id)
        # site_label etiqueta el campus (multi-campus). None = mono-campus (header
        # clásico, sin cambios para el caso mayoritario).
        message = self.message_builder.build_changes_message(diff, site_label=site_label)

        logger.info("Sending notification for user_id=%s", user.id)
        await self.notifier.send_message(user, message)

        logger.info("Notification sent for user_id=%s", user.id)
        return True