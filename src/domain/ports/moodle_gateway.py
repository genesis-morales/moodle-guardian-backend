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

    @abstractmethod
    async def get_forums(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[CalendarEvent]:
        """Foros con fecha de entrega, como CalendarEvent (module='forum').

        Necesario porque Moodle solo crea evento de calendario a partir del
        `duedate`; un foro cuya fecha está en `cutoffdate` es invisible para
        get_calendar_events. Aquí los recuperamos directo del módulo forum.
        """
        raise NotImplementedError