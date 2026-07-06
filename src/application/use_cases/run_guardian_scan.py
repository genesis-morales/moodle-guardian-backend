import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from src.application.dto.sync_dto import ManualSyncInput, ManualSyncOutput
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.notify_user_changes import NotifyUserChangesUseCase
from src.domain.entities.announcement import Announcement
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.message import Message
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.snapshot import DeliverableRef, Snapshot
from src.domain.entities.source_type import SourceType
from src.domain.entities.user import User
from src.domain.ports.snapshot_repository import SnapshotRepository
from src.domain.ports.user_repository import UserRepository
from src.domain.services.diff_service import DiffService

logger = logging.getLogger(__name__)


def snapshot_from_sync_output(user_id: int, data: ManualSyncOutput) -> Snapshot:
    """Convierte la salida de sincronización (DTO) en un Snapshot de dominio.

    Compartido entre el scan real y el preview de debug para no duplicar el
    mapeo DTO -> entidades.
    """
    assignments = [
        Assignment(
            moodle_assignment_id=item.moodle_assignment_id,
            moodle_course_id=item.moodle_course_id,
            name=item.name,
            due_date=datetime.fromtimestamp(item.due_date, UTC)
            if item.due_date is not None
            else None,
            allow_submissions_from=datetime.fromtimestamp(
                item.allow_submissions_from, UTC
            )
            if item.allow_submissions_from is not None
            else None,
            cutoff_date=datetime.fromtimestamp(item.cutoff_date, UTC)
            if item.cutoff_date is not None
            else None,
            course_name=item.course_name,
        )
        for item in data.assignments
    ]

    events = [
        CalendarEvent(
            moodle_event_id=item.moodle_event_id,
            course_id=item.course_id,
            name=item.name,
            event_type=item.event_type,
            due_date=datetime.fromtimestamp(item.due_date, UTC)
            if item.due_date is not None
            else None,
            url=item.url,
            module=item.module,
            course_name=item.course_name,
        )
        for item in data.events
    ]

    instructions = [
        Instruction(
            moodle_id=item.moodle_id,
            course_id=item.course_id,
            name=item.name,
            url=item.url,
            content_fingerprint=item.content_fingerprint,
            kind=item.kind,
            course_name=item.course_name,
        )
        for item in data.instructions
    ]

    announcements = [
        Announcement(
            discussion_id=item.discussion_id,
            course_id=item.course_id,
            name=item.name,
            content_fingerprint=item.content_fingerprint,
            url=item.url,
            author=item.author,
            posted_at=datetime.fromtimestamp(item.posted_at, UTC)
            if item.posted_at is not None
            else None,
            course_name=item.course_name,
        )
        for item in data.announcements
    ]

    messages = [
        Message(
            message_id=item.message_id,
            sender_name=item.sender_name,
            preview=item.preview,
            sent_at=datetime.fromtimestamp(item.sent_at, UTC)
            if item.sent_at is not None
            else None,
            conversation_id=item.conversation_id,
            sender_id=item.sender_id,
            url=item.url,
        )
        for item in data.messages
    ]

    deliverable_refs = [
        DeliverableRef(course_id=item.course_id, name=item.name)
        for item in data.deliverable_refs
    ]

    return Snapshot(
        user_id=user_id,
        moodle_user_id=data.moodle_user_id,
        captured_at=datetime.now(UTC),
        assignments=assignments,
        events=events,
        instructions=instructions,
        deliverable_refs=deliverable_refs,
        items={
            SourceType.ANNOUNCEMENT: announcements,
            SourceType.MESSAGE: messages,
        },
    )


@dataclass
class RunGuardianScanResult:
    user: User
    previous_snapshot: Optional[Snapshot]
    current_snapshot: Snapshot
    diff: DiffResult
    notification_sent: bool


class RunGuardianScanUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        snapshot_repository: SnapshotRepository,
        fetch_course_snapshot_use_case: FetchCourseSnapshotUseCase,
        diff_service: DiffService,
        notify_user_changes_use_case: NotifyUserChangesUseCase,
    ) -> None:
        self.user_repository = user_repository
        self.snapshot_repository = snapshot_repository
        self.fetch_course_snapshot_use_case = fetch_course_snapshot_use_case
        self.diff_service = diff_service
        self.notify_user_changes_use_case = notify_user_changes_use_case

    async def execute(self, moodle_user_id: int) -> RunGuardianScanResult:
        logger.info("Starting guardian scan for moodle_user_id=%s", moodle_user_id)

        user = await self.user_repository.get_by_moodle_user_id(moodle_user_id)
        if user is None:
            logger.warning("Guardian scan failed: user not found for moodle_user_id=%s", moodle_user_id)
            raise ValueError("User not found")

        logger.info("User found for moodle_user_id=%s user_id=%s", moodle_user_id, user.id)

        previous_snapshot = await self.snapshot_repository.get_latest_by_user_id(user.id)
        logger.info(
            "Previous snapshot %s for user_id=%s",
            "found" if previous_snapshot is not None else "not found",
            user.id,
        )

        sync_output = await self.fetch_course_snapshot_use_case.execute(
            ManualSyncInput(moodle_user_id=moodle_user_id)
        )
        logger.info(
            "Fetched course snapshot for moodle_user_id=%s assignments=%s events=%s instructions=%s",
            moodle_user_id,
            len(sync_output.assignments),
            len(sync_output.events),
            len(sync_output.instructions),
        )

        current_snapshot = self._to_snapshot(user.id, sync_output)
        logger.info("Current snapshot built for user_id=%s", user.id)

        if previous_snapshot is None:
            diff = DiffResult()
            logger.info("No previous snapshot found, using empty diff for user_id=%s", user.id)
        else:
            diff = self.diff_service.compare(previous_snapshot, current_snapshot)
            logger.info("Diff calculated for user_id=%s has_changes=%s", user.id, diff.has_changes)

        # Notificamos ANTES de guardar el snapshot. El snapshot es el "baseline"
        # contra el que se calcula el próximo diff: si lo guardáramos primero y
        # el envío de Telegram fallara (timeout, red del runner...), el cambio
        # quedaría consumido en el baseline y nunca se reintentaría -> aviso
        # perdido. Al notificar primero, un fallo de envío propaga la excepción
        # y el snapshot NO se guarda, así que el próximo scan vuelve a detectar
        # el cambio y reintenta. El riesgo inverso (envío OK pero save falla ->
        # posible aviso duplicado) es preferible a perder un aviso.
        notification_sent = await self.notify_user_changes_use_case.execute(
            user=user,
            diff=diff,
        )

        await self.snapshot_repository.save(current_snapshot)
        logger.info("Snapshot saved for user_id=%s", user.id)

        logger.info(
            "Guardian scan completed for user_id=%s notification_sent=%s",
            user.id,
            notification_sent,
        )

        return RunGuardianScanResult(
            user=user,
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
            diff=diff,
            notification_sent=notification_sent,
        )

    def _to_snapshot(self, user_id: int, data: ManualSyncOutput) -> Snapshot:
        return snapshot_from_sync_output(user_id, data)