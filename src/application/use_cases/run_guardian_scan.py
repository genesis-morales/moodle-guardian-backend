from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from src.application.dto.sync_dto import ManualSyncInput, ManualSyncOutput
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.application.use_cases.notify_user_changes import NotifyUserChangesUseCase
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.user import User
from src.domain.ports.snapshot_repository import SnapshotRepository
from src.domain.ports.user_repository import UserRepository
from src.domain.services.diff_service import DiffService


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
            notify_user_changes_use_case: NotifyUserChangesUseCase,) -> None:
        self.user_repository = user_repository
        self.snapshot_repository = snapshot_repository
        self.fetch_course_snapshot_use_case = fetch_course_snapshot_use_case
        self.diff_service = diff_service
        self.notify_user_changes_use_case = notify_user_changes_use_case

    async def execute(self, moodle_user_id: int) -> RunGuardianScanResult:
        user = await self.user_repository.get_by_moodle_user_id(moodle_user_id)
        if user is None:
            raise ValueError("User not found")

        previous_snapshot = await self.snapshot_repository.get_latest_by_user_id(user.id)

        sync_output = await self.fetch_course_snapshot_use_case.execute(ManualSyncInput(moodle_user_id=moodle_user_id))

        current_snapshot = self._to_snapshot(user.id, sync_output)

        if previous_snapshot is None:
            diff = DiffResult()
        else:
            diff = self.diff_service.compare(previous_snapshot, current_snapshot)

        await self.snapshot_repository.save(current_snapshot)

        notification_sent = await self.notify_user_changes_use_case.execute(user=user, diff=diff,)

        return RunGuardianScanResult(
            user=user,
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
            diff=diff,
            notification_sent=notification_sent,
        )

    def _to_snapshot(self, user_id: int, data: ManualSyncOutput) -> Snapshot:
        assignments = [
            Assignment(
                moodle_assignment_id=item.moodle_assignment_id,
                moodle_course_id=item.moodle_course_id,
                name=item.name,
                due_date=datetime.fromtimestamp(item.due_date, UTC)
                if item.due_date is not None else None,
                allow_submissions_from=datetime.fromtimestamp(
                    item.allow_submissions_from, UTC
                )
                if item.allow_submissions_from is not None else None,
                cutoff_date=datetime.fromtimestamp(item.cutoff_date, UTC)
                if item.cutoff_date is not None else None,
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
                if item.due_date is not None else None,
                url=item.url,
            )
            for item in data.events
        ]

        return Snapshot(
            user_id=user_id,
            moodle_user_id=data.moodle_user_id,
            captured_at=datetime.now(UTC),
            assignments=assignments,
            events=events,
        )