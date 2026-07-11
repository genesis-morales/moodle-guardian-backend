import logging

from src.application.notification_subjects import SUBJECT_DIGEST
from src.application.ports.notification_dispatcher import NotificationDispatcher
from src.application.use_cases.build_weekly_digest import BuildWeeklyDigestUseCase
from src.domain.ports.sent_reminder_repository import (
    NOTIFICATION_WEEKLY_DIGEST,
    SentReminderRepository,
)
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SendWeeklyDigestUseCase:
    """Envía el digest semanal a todos los usuarios activos y registra el envío
    en el historial (auditoría; el digest no necesita dedup, va por cron)."""

    def __init__(
        self,
        user_repository: UserRepository,
        build_weekly_digest_use_case: BuildWeeklyDigestUseCase,
        dispatcher: NotificationDispatcher,
        sent_reminder_repository: SentReminderRepository,
    ) -> None:
        self.user_repository = user_repository
        self.build_weekly_digest_use_case = build_weekly_digest_use_case
        self.dispatcher = dispatcher
        self.sent_reminder_repository = sent_reminder_repository

    async def execute(self) -> int:
        users = await self.user_repository.list_active()
        logger.info("Sending weekly digest count=%s", len(users))

        sent = 0
        for user in users:
            try:
                items = await self.build_weekly_digest_use_case.collect_items(
                    user.moodle_user_id
                )
                delivered = await self.dispatcher.dispatch(
                    user,
                    lambda builder, items=items: builder.build_weekly_digest_message(
                        items
                    ),
                    subject=SUBJECT_DIGEST,
                )
                if not delivered:
                    continue
                await self.sent_reminder_repository.record(
                    user_id=user.id,
                    notification_type=NOTIFICATION_WEEKLY_DIGEST,
                    deliverable_key=None,
                    deadline_snapshot=None,
                )
                sent += 1
            except Exception:
                logger.exception("Weekly digest failed for user_id=%s", user.id)

        logger.info("Weekly digest finished sent=%s total=%s", sent, len(users))
        return sent
