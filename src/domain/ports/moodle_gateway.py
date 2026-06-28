from abc import ABC, abstractmethod

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
from src.domain.entities.instruction import Instruction


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
        """Foros del curso, como CalendarEvent (module='forum').

        Necesario porque Moodle solo crea evento de calendario a partir del
        `duedate`; un foro cuya fecha está en `cutoffdate` es invisible para
        get_calendar_events. Aquí los recuperamos directo del módulo forum.

        Devuelve TODOS los foros, incluso sin fecha (`due_date=None`): los que
        tienen plazo alimentan recordatorios; los que no, sirven igual para
        absorber su PDF de instrucciones. El consumidor filtra por fecha lo que
        necesite notificar.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_course_resources(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[Instruction]:
        """Recursos de archivo (PDFs de instrucciones) de cada curso.

        Obtenidos de `core_course_get_contents`, filtrando módulos `resource` y
        `folder`. Cada archivo se devuelve como una Instruction (un `folder`
        puede contener varios archivos). `content_fingerprint` se deriva del
        `timemodified` del archivo para detectar cambios de contenido.
        """
        raise NotImplementedError