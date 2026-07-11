import logging

from src.application.notification_subjects import SUBJECT_REMINDER
from src.application.ports.notification_dispatcher import NotificationDispatcher
from src.application.use_cases.build_deadline_reminder import (
    BuildDeadlineReminderUseCase,
)
from src.domain.ports.sent_reminder_repository import (
    NOTIFICATION_REMINDER,
    SentReminderRepository,
)
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SendDeadlineRemindersUseCase:
    """Envía el recordatorio de entregas próximas a los usuarios activos y
    registra cada envío en el historial para no repetirlo."""

    def __init__(
        self,
        user_repository: UserRepository,
        build_deadline_reminder_use_case: BuildDeadlineReminderUseCase,
        dispatcher: NotificationDispatcher,
        sent_reminder_repository: SentReminderRepository,
    ) -> None:
        self.user_repository = user_repository
        self.build_deadline_reminder_use_case = build_deadline_reminder_use_case
        self.dispatcher = dispatcher
        self.sent_reminder_repository = sent_reminder_repository

    async def execute(self) -> int:
        users = await self.user_repository.list_active()
        logger.info("Sending deadline reminders count=%s", len(users))

        sent = 0
        for user in users:
            try:
                preview = await self.build_deadline_reminder_use_case.execute(
                    user.moodle_user_id
                )
                if not preview.items:
                    continue

                delivered = await self.dispatcher.dispatch(
                    user,
                    lambda builder, p=preview: builder.build_deadline_reminder_message(
                        p.items, p.days
                    ),
                    subject=SUBJECT_REMINDER,
                )
                if not delivered:
                    continue

                # Registramos cada entregable avisado (su fecha actual) para no
                # repetir el recordatorio salvo que la fecha cambie.
                for item in preview.items:
                    await self.sent_reminder_repository.record(
                        user_id=user.id,
                        notification_type=NOTIFICATION_REMINDER,
                        deliverable_key=item.key,
                        deadline_snapshot=item.deadline,
                    )

                sent += 1
            except Exception:
                logger.exception("Deadline reminder failed for user_id=%s", user.id)

        logger.info("Deadline reminders finished sent=%s total=%s", sent, len(users))
        return sent
