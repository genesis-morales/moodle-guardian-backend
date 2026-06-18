from datetime import UTC, datetime, timedelta

from src.application.dto.sync_dto import (
    AssignmentItemOutput,
    CalendarEventItemOutput,
    ManualSyncInput,
    ManualSyncOutput,
)
from src.domain.exceptions.domain_errors import DomainError
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.user_repository import UserRepository


class FetchCourseSnapshotUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        moodle_gateway: MoodleGateway,
    ) -> None:
        self.user_repository = user_repository
        self.moodle_gateway = moodle_gateway

    async def execute(self, data: ManualSyncInput) -> ManualSyncOutput:
        user = await self.user_repository.get_by_moodle_user_id(data.moodle_user_id)
        if user is None:
            raise DomainError("Usuario no encontrado.")

        now = datetime.now(UTC)

        all_courses = await self.moodle_gateway.get_courses(
            token=user.moodle_token,
            moodle_user_id=user.moodle_user_id,
        )

        # Solo cursos del cuatrimestre vigente: descartamos los que ya cerraron
        # (cuatrimestres anteriores) para no notificar actividades de cursos que
        # el usuario ya no está cursando.
        courses = [course for course in all_courses if course.is_active(now)]

        course_ids = [course.moodle_course_id for course in courses]
        course_names = {
            course.moodle_course_id: course.fullname for course in courses
        }

        all_assignments = await self.moodle_gateway.get_assignments(
            token=user.moodle_token,
            course_ids=course_ids,
        )

        # A diferencia de los eventos (que ya vienen con ventana temporal), las
        # tareas llegan completas. Descartamos las ya vencidas para no arrastrar
        # entregas de avances/cuatrimestres pasados.
        assignments = [a for a in all_assignments if not a.is_past(now)]

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
                    course_name=course_names.get(item.moodle_course_id),
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
                    module=item.module,
                    course_name=course_names.get(item.course_id),
                )
                for item in events
            ],
        )