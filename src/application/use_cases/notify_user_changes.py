from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User
from src.domain.ports.notifier_gateway import NotifierGateway


class NotifyUserChangesUseCase:
    def __init__(
        self,
        notifier: NotifierGateway,
        message_builder: NotificationMessageBuilder,
    ) -> None:
        self.notifier = notifier
        self.message_builder = message_builder

    async def execute(self, user: User, diff: DiffResult) -> bool:
        if not diff.has_changes:
            return False

        if not user.telegram_chat_id:
            return False

        message = self.message_builder.build_changes_message(diff)
        await self.notifier.send_message(user, message)
        return True