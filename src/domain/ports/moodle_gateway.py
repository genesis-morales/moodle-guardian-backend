from typing import Protocol, List

from src.domain.entities.course import Course
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent


class MoodleGateway(Protocol):
    async def validate_token(self, token: str) -> bool:
        ...

    async def get_courses(self, token: str, moodle_user_id: int) -> List[Course]:
        ...

    async def get_assignments(
        self,
        token: str,
        moodle_user_id: int,
        course_ids: List[int],
    ) -> List[Assignment]:
        ...

    async def get_calendar_events(
        self,
        token: str,
        moodle_user_id: int,
    ) -> List[CalendarEvent]:
        ...