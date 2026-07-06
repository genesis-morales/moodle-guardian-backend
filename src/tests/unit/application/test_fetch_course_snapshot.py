from datetime import UTC, datetime, timedelta

import pytest
from unittest.mock import AsyncMock, Mock

from src.application.dto.sync_dto import ManualSyncInput
from src.application.use_cases.fetch_course_snapshot import FetchCourseSnapshotUseCase
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
from src.domain.entities.instruction import Instruction
from src.domain.entities.user import User

pytestmark = pytest.mark.anyio

COURSE_ID = 20
NOW = datetime.now(UTC)
SOON = NOW + timedelta(days=5)


def build_user() -> User:
    return User(
        id=1,
        moodle_user_id=3095,
        moodle_token="token-123",
        telegram_chat_id="chat-123",
    )


def build_gateway(
    *,
    assignments: list[Assignment] | None = None,
    events: list[CalendarEvent] | None = None,
    forums: list[CalendarEvent] | None = None,
    resources: list[Instruction] | None = None,
    announcements: list | None = None,
    messages: list | None = None,
) -> Mock:
    gateway = Mock()
    gateway.get_courses = AsyncMock(
        return_value=[
            Course(
                id=None,
                moodle_course_id=COURSE_ID,
                fullname="Curso de prueba",
                shortname="CP",
                end_date=None,  # sin fecha de cierre -> vigente
            )
        ]
    )
    gateway.get_assignments = AsyncMock(return_value=assignments or [])
    gateway.get_calendar_events = AsyncMock(return_value=events or [])
    gateway.get_forums = AsyncMock(return_value=forums or [])
    gateway.get_course_resources = AsyncMock(return_value=resources or [])
    gateway.get_announcements = AsyncMock(return_value=announcements or [])
    gateway.get_messages = AsyncMock(return_value=messages or [])
    return gateway


def build_use_case(gateway: Mock) -> FetchCourseSnapshotUseCase:
    user_repository = Mock()
    user_repository.get_by_moodle_user_id = AsyncMock(return_value=build_user())
    return FetchCourseSnapshotUseCase(
        user_repository=user_repository,
        moodle_gateway=gateway,
    )


def resource(name: str) -> Instruction:
    return Instruction(moodle_id=1, course_id=COURSE_ID, name=name, content_fingerprint="1")


def due_event(name: str) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=30,
        course_id=COURSE_ID,
        name=name,
        event_type="due",
        due_date=SOON,
        module="assign",
    )


async def test_calendar_due_event_is_added_to_deliverable_refs():
    # En algunos Moodle el "espacio de entrega" llega como evento "due" y no
    # como mod_assign: debe entrar igual a deliverable_refs.
    gateway = build_gateway(events=[due_event("Tarea 1")])
    output = await build_use_case(gateway).execute(ManualSyncInput(moodle_user_id=3095))

    refs = [(r.course_id, r.name) for r in output.deliverable_refs]
    assert (COURSE_ID, "Tarea 1") in refs


async def test_instruction_is_absorbed_by_matching_calendar_event():
    gateway = build_gateway(
        events=[due_event("Tarea 1")],
        resources=[resource("Instrucciones Tarea 1"), resource("Examen final")],
    )
    output = await build_use_case(gateway).execute(ManualSyncInput(moodle_user_id=3095))

    names = [i.name for i in output.instructions]
    # "Instrucciones Tarea 1" la absorbe el evento "Tarea 1"; "Examen final" no
    # tiene entregable que la cubra, así que sobrevive.
    assert names == ["Examen final"]

    # La absorbida queda registrada en debug con quién la absorbió.
    absorbed = [(a.name, a.absorbed_by) for a in output.absorbed_instructions]
    assert absorbed == [("Instrucciones Tarea 1", "Tarea 1")]


async def test_generic_forum_does_not_absorb_unrelated_instruction():
    # Un foro genérico del curso no debe absorber un PDF que no le corresponde.
    forum = CalendarEvent(
        moodle_event_id=None,
        course_id=COURSE_ID,
        name="Foro de Consulta",
        event_type="due",
        due_date=None,
        module="forum",
    )
    gateway = build_gateway(forums=[forum], resources=[resource("Tarea 1")])
    output = await build_use_case(gateway).execute(ManualSyncInput(moodle_user_id=3095))

    assert [i.name for i in output.instructions] == ["Tarea 1"]


async def test_forum_instruction_pdf_is_not_notified():
    # Los PDF de foro no se tratan como instrucción de entregable.
    gateway = build_gateway(resources=[resource("Foro No.1"), resource("Tarea No.1")])
    output = await build_use_case(gateway).execute(ManualSyncInput(moodle_user_id=3095))

    assert [i.name for i in output.instructions] == ["Tarea No.1"]
