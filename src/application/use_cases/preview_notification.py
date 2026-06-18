import logging
from dataclasses import dataclass

from src.application.dto.sync_dto import ManualSyncInput
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.run_guardian_scan import snapshot_from_sync_output
from src.domain.entities.diff_result import DiffResult
from src.domain.ports.notifier_gateway import NotifierGateway
from src.domain.ports.snapshot_repository import SnapshotRepository
from src.domain.ports.user_repository import UserRepository
from src.domain.services.diff_service import DiffService

logger = logging.getLogger(__name__)

MODE_DIFF = "diff"
MODE_ALL = "all"


@dataclass
class PreviewResult:
    moodle_user_id: int
    mode: str
    has_changes: bool
    message: str
    sent: bool
    events_new: int
    events_updated: int
    events_removed: int
    assignments_new: int
    assignments_updated: int
    assignments_removed: int


class PreviewNotificationUseCase:
    """Debug read-only: arma el mensaje que se notificaría, sin guardar snapshot.

    - mode="diff": compara contra el último snapshot (lo que SÍ dispararía).
    - mode="all": trata todo lo actual como nuevo (para revisar formato).
    Con send=True, además entrega el mensaje al Telegram del usuario.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        snapshot_repository: SnapshotRepository,
        fetch_course_snapshot_use_case: FetchCourseSnapshotUseCase,
        diff_service: DiffService,
        message_builder: NotificationMessageBuilder,
        notifier: NotifierGateway,
    ) -> None:
        self.user_repository = user_repository
        self.snapshot_repository = snapshot_repository
        self.fetch_course_snapshot_use_case = fetch_course_snapshot_use_case
        self.diff_service = diff_service
        self.message_builder = message_builder
        self.notifier = notifier

    async def execute(
        self,
        moodle_user_id: int,
        mode: str = MODE_DIFF,
        send: bool = False,
    ) -> PreviewResult:
        if mode not in (MODE_DIFF, MODE_ALL):
            raise ValueError(f"mode inválido: {mode!r} (usa 'diff' o 'all')")

        user = await self.user_repository.get_by_moodle_user_id(moodle_user_id)
        if user is None:
            raise ValueError("User not found")

        sync_output = await self.fetch_course_snapshot_use_case.execute(
            ManualSyncInput(moodle_user_id=moodle_user_id)
        )
        current_snapshot = snapshot_from_sync_output(user.id, sync_output)

        if mode == MODE_ALL:
            diff = DiffResult(
                new_assignments=list(current_snapshot.assignments),
                new_events=list(current_snapshot.events),
            )
        else:
            previous = await self.snapshot_repository.get_latest_by_user_id(user.id)
            diff = self.diff_service.compare(previous, current_snapshot)

        message = self.message_builder.build_changes_message(diff)

        sent = False
        if send and user.telegram_chat_id and diff.has_changes:
            await self.notifier.send_message(user, message)
            sent = True
            logger.info("Preview enviado a Telegram para moodle_user_id=%s", moodle_user_id)

        return PreviewResult(
            moodle_user_id=moodle_user_id,
            mode=mode,
            has_changes=diff.has_changes,
            message=message,
            sent=sent,
            events_new=len(diff.new_events),
            events_updated=len(diff.updated_events),
            events_removed=len(diff.removed_events),
            assignments_new=len(diff.new_assignments),
            assignments_updated=len(diff.updated_assignments),
            assignments_removed=len(diff.removed_assignments),
        )
