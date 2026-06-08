from datetime import UTC, datetime, timedelta

from src.application.dto.sync_dto import (
    AssignmentItemOutput,
    CalendarEventItemOutput,
    ManualSyncInput,
    ManualSyncOutput,
)
from src.domain.exceptions.domain_errors import DomainError
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.subscription_repository import SubscriptionRepository
from src.domain.ports.user_repository import UserRepository


class FetchCourseSnapshotUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
        moodle_gateway: MoodleGateway,
    ) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.moodle_gateway = moodle_gateway

    async def execute(self, data: ManualSyncInput) -> ManualSyncOutput:
        user = await self.user_repository.get_by_moodle_user_id(data.moodle_user_id)
        if user is None:
            raise DomainError("Usuario no encontrado.")

        courses = await self.moodle_gateway.get_courses(
            token=user.moodle_token,
            moodle_user_id=user.moodle_user_id,
        )

        course_ids = [course.moodle_course_id for course in courses]

        await self.subscription_repository.replace_user_courses(
            user_id=user.id,
            course_ids=course_ids,
        )

        assignments = await self.moodle_gateway.get_assignments(
            token=user.moodle_token,
            course_ids=course_ids,
        )

        now = datetime.now(UTC)
        in_30_days = now + timedelta(days=30)

        events = await self.moodle_gateway.get_calendar_events(
            token=user.moodle_token,
            course_ids=course_ids,
            timestart=int(now.timestamp()),
            timeend=int(in_30_days.timestamp()),
        )

        return ManualSyncOutput(
            moodle_user_id=user.moodle_user_id,
            courses_count=len(course_ids),
            assignments_count=len(assignments),
            events_count=len(events),
            assignments=[
                AssignmentItemOutput(
                    moodle_assignment_id=item.moodle_assignment_id,
                    moodle_course_id=item.moodle_course_id,
                    name=item.name,
                    due_date=int(item.due_date.timestamp()) if item.due_date else None,
                    allow_submissions_from=int(item.allow_submissions_from.timestamp())
                    if item.allow_submissions_from else None,
                    cutoff_date=int(item.cutoff_date.timestamp()) if item.cutoff_date else None,
                )
                for item in assignments
            ],
            events=[
                CalendarEventItemOutput(
                    moodle_event_id=item.moodle_event_id,
                    course_id=item.course_id,
                    name=item.name,
                    event_type=item.event_type,
                    due_date=int(item.due_date.timestamp()) if item.due_date else None,
                    url=item.url,
                )
                for item in events
            ],
        )