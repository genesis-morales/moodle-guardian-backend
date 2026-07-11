from datetime import UTC, datetime

from src.application.dto.sync_dto import ManualSyncInput
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.run_guardian_scan import snapshot_from_sync_output
from src.domain.services import digest_service


class BuildWeeklyDigestUseCase:
    """Construye el mensaje del digest semanal de un usuario: todas las
    entregas pendientes futuras, en orden cronológico."""

    def __init__(
        self,
        fetch_course_snapshot_use_case: FetchCourseSnapshotUseCase,
        message_builder: NotificationMessageBuilder,
    ) -> None:
        self.fetch_course_snapshot_use_case = fetch_course_snapshot_use_case
        self.message_builder = message_builder

    async def collect_items(self, moodle_user_id: int):
        """Entregables pendientes futuros (sin renderizar). El envío multicanal los
        renderiza por canal; el preview de debug usa `execute` (string Telegram)."""
        sync = await self.fetch_course_snapshot_use_case.execute(
            ManualSyncInput(moodle_user_id=moodle_user_id)
        )
        snapshot = snapshot_from_sync_output(0, sync)

        now = datetime.now(UTC)
        items = digest_service.collect_deliverables(
            snapshot.assignments, snapshot.events
        )
        return digest_service.filter_future(items, now)

    async def execute(self, moodle_user_id: int) -> str:
        items = await self.collect_items(moodle_user_id)
        return self.message_builder.build_weekly_digest_message(items)
