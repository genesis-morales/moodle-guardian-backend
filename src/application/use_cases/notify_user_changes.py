import logging

from src.application.notification_subjects import SUBJECT_CHANGES
from src.application.ports.notification_dispatcher import NotificationDispatcher
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User

logger = logging.getLogger(__name__)


class NotifyUserChangesUseCase:
    def __init__(self, dispatcher: NotificationDispatcher) -> None:
        self.dispatcher = dispatcher

    async def execute(
        self, user: User, diff: DiffResult, site_label: str | None = None
    ) -> bool:
        logger.info("Evaluating notification for user_id=%s", user.id)

        if not diff.has_changes:
            logger.info("Notification skipped: no changes for user_id=%s", user.id)
            return False

        # El dispatcher resuelve los canales activos de la cuenta (Telegram/email…) y
        # arma el cuerpo por canal. Si la cuenta no tiene canales entregables, devuelve
        # False (skip); si hay canales pero todos fallan, levanta (el scan reintenta).
        logger.info("Dispatching notification for user_id=%s", user.id)
        sent = await self.dispatcher.dispatch(
            user,
            lambda builder: builder.build_changes_message(diff, site_label=site_label),
            subject=SUBJECT_CHANGES,
        )
        if sent:
            logger.info("Notification sent for user_id=%s", user.id)
        else:
            logger.info(
                "Notification skipped: no deliverable channels for user_id=%s", user.id
            )
        return sent
