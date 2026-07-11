from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.dto.digest_dto import DeliverableItem
from src.application.dto.sync_dto import ManualSyncInput
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.run_guardian_scan import snapshot_from_sync_output
from src.config.settings import get_settings
from src.domain.ports.sent_reminder_repository import (
    NOTIFICATION_REMINDER,
    SentReminderRepository,
)
from src.domain.ports.user_repository import UserRepository
from src.domain.services import digest_service


@dataclass
class ReminderPreview:
    """Resultado del build: el mensaje a enviar (o None si no hay nada nuevo) y
    los entregables incluidos, para que el envío real los registre en el historial.
    `days` es el horizonte usado (lo necesita el envío multicanal para re-renderizar
    el cuerpo por cada canal con el mismo encabezado)."""

    message: str | None
    items: list[DeliverableItem]
    days: int = 0


class BuildDeadlineReminderUseCase:
    """Construye el recordatorio de entregas que vencen dentro de
    `reminder_days_before` días y que aún no se han notificado para esa fecha.

    Solo LEE el historial (no escribe); el registro lo hace el envío real. Si la
    fecha de una entrega cambió respecto a lo ya notificado, se vuelve a incluir.
    """

    def __init__(
        self,
        fetch_course_snapshot_use_case: FetchCourseSnapshotUseCase,
        message_builder: NotificationMessageBuilder,
        user_repository: UserRepository,
        sent_reminder_repository: SentReminderRepository,
    ) -> None:
        self.fetch_course_snapshot_use_case = fetch_course_snapshot_use_case
        self.message_builder = message_builder
        self.user_repository = user_repository
        self.sent_reminder_repository = sent_reminder_repository

    async def execute(self, moodle_user_id: int, days: int | None = None) -> ReminderPreview:
        settings = get_settings()
        if days is None:
            days = settings.reminder_days_before
        tz = ZoneInfo(settings.timezone)

        user = await self.user_repository.get_by_moodle_user_id(moodle_user_id)
        if user is None:
            return ReminderPreview(message=None, items=[], days=days)

        sync = await self.fetch_course_snapshot_use_case.execute(
            ManualSyncInput(moodle_user_id=moodle_user_id)
        )
        snapshot = snapshot_from_sync_output(user.id, sync)

        now = datetime.now(tz)
        items = digest_service.collect_deliverables(
            snapshot.assignments, snapshot.events
        )
        items = digest_service.filter_due_within(items, now, days, tz)

        # Read-only: excluimos lo ya notificado para esa misma fecha. Si la fecha
        # cambió (o nunca se avisó), se incluye.
        already = await self.sent_reminder_repository.latest_deadlines(
            user.id, NOTIFICATION_REMINDER
        )
        pending = [item for item in items if already.get(item.key) != item.deadline]

        if not pending:
            return ReminderPreview(message=None, items=[], days=days)

        message = self.message_builder.build_deadline_reminder_message(pending, days)
        return ReminderPreview(message=message, items=pending, days=days)
