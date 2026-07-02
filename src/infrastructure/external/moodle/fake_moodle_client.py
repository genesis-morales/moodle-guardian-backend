"""Fake de Moodle para los perfiles `local`/`dev` del factory de entornos.

Devuelve un set de datos canónico y **determinista** (fechas fijas en el futuro,
para que sean accionables y no generen diffs espurios entre corridas), de modo que
se pueda desarrollar y probar el pipeline completo (scan → snapshot → diff → notify)
sin pegarle a la Moodle real de UNED. Implementa el mismo puerto que `MoodleClient`.
"""

from datetime import UTC, datetime

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
from src.domain.entities.instruction import Instruction
from src.domain.ports.moodle_gateway import MoodleGateway

# Fechas fijas y lejanas: siempre "futuras"/accionables y estables entre corridas.
_FUTURE = datetime(2030, 3, 1, 12, 0, tzinfo=UTC)
_FUTURE_LATER = datetime(2030, 5, 15, 12, 0, tzinfo=UTC)
_FUTURE_QUIZ = datetime(2030, 2, 20, 12, 0, tzinfo=UTC)

# Cursos canónicos del fake (sin end_date => vigentes).
_COURSES = [
    Course(id=None, moodle_course_id=101, fullname="Introducción a la Programación",
           shortname="PROG-101", visible=True),
    Course(id=None, moodle_course_id=102, fullname="Bases de Datos",
           shortname="BD-102", visible=True),
]


class FakeMoodleClient(MoodleGateway):
    async def validate_token(self, token: str) -> bool:
        # En local/dev cualquier token es válido: permite registrar usuarios de prueba.
        return True

    async def get_courses(self, token: str, moodle_user_id: int) -> list[Course]:
        return list(_COURSES)

    async def get_assignments(
        self, token: str, course_ids: list[int]
    ) -> list[Assignment]:
        if not course_ids:
            return []
        catalog = [
            Assignment(moodle_assignment_id=5001, moodle_course_id=101,
                       name="Tarea 1 - Introducción", due_date=_FUTURE),
            Assignment(moodle_assignment_id=5002, moodle_course_id=102,
                       name="Proyecto Final", due_date=_FUTURE_LATER),
        ]
        return [a for a in catalog if a.moodle_course_id in course_ids]

    async def get_calendar_events(
        self, token: str, course_ids: list[int], timestart: int, timeend: int
    ) -> list[CalendarEvent]:
        catalog = [
            CalendarEvent(moodle_event_id=9001, course_id=101, name="Quiz 1",
                          event_type="due", due_date=_FUTURE_QUIZ, module="quiz"),
        ]
        return [e for e in catalog if e.course_id in course_ids]

    async def get_forums(self, token: str, course_ids: list[int]) -> list[CalendarEvent]:
        if not course_ids:
            return []
        # Igual que el real: moodle_event_id=None, module="forum".
        catalog = [
            CalendarEvent(moodle_event_id=None, course_id=101, name="Foro Semana 1",
                          event_type="due", due_date=_FUTURE, module="forum"),
        ]
        return [e for e in catalog if e.course_id in course_ids]

    async def get_course_resources(
        self, token: str, course_ids: list[int]
    ) -> list[Instruction]:
        catalog = [
            Instruction(moodle_id=7001, course_id=101,
                        name="Instrucciones Tarea 1.pdf",
                        url="https://fake.moodle/local/tarea1.pdf",
                        content_fingerprint="1700000000", kind="resource"),
        ]
        return [i for i in catalog if i.course_id in course_ids]
