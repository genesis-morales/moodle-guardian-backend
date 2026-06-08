from abc import ABC, abstractmethod

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course


class MoodleGateway(ABC):
    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_courses(self, token: str, moodle_user_id: int) -> list[Course]:
        raise NotImplementedError

    @abstractmethod
    async def get_assignments(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[Assignment]:
        raise NotImplementedError

    @abstractmethod
    async def get_calendar_events(
        self,
        token: str,
        course_ids: list[int],
        timestart: int,
        timeend: int,
    ) -> list[CalendarEvent]:
        raise NotImplementedError