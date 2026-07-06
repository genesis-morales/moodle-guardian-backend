import pytest

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
from src.domain.entities.instruction import Instruction
from src.infrastructure.external.moodle.fake_moodle_client import FakeMoodleClient

pytestmark = pytest.mark.anyio

_ALL_COURSES = [101, 102]


async def test_validate_token_always_true():
    assert await FakeMoodleClient().validate_token("cualquier-cosa") is True


async def test_get_courses_returns_courses():
    courses = await FakeMoodleClient().get_courses("t", moodle_user_id=1)
    assert len(courses) == 2
    assert all(isinstance(c, Course) for c in courses)


async def test_get_assignments_filters_by_course_and_empty():
    client = FakeMoodleClient()
    assigns = await client.get_assignments("t", _ALL_COURSES)
    assert len(assigns) == 2
    assert all(isinstance(a, Assignment) for a in assigns)
    # Filtra por curso pedido.
    only_101 = await client.get_assignments("t", [101])
    assert [a.moodle_course_id for a in only_101] == [101]
    # Sin cursos -> lista vacía (igual que el real).
    assert await client.get_assignments("t", []) == []


async def test_get_calendar_events():
    events = await FakeMoodleClient().get_calendar_events("t", _ALL_COURSES, 0, 0)
    assert all(isinstance(e, CalendarEvent) for e in events)
    assert any(e.name == "Quiz 1" for e in events)


async def test_get_forums_shape_and_empty():
    client = FakeMoodleClient()
    forums = await client.get_forums("t", _ALL_COURSES)
    assert forums and all(f.module == "forum" and f.moodle_event_id is None for f in forums)
    assert await client.get_forums("t", []) == []


async def test_get_course_resources():
    res = await FakeMoodleClient().get_course_resources("t", _ALL_COURSES)
    assert all(isinstance(i, Instruction) for i in res)
    assert any(i.name.lower().endswith(".pdf") for i in res)


async def test_deterministic_between_calls():
    client = FakeMoodleClient()
    a = await client.get_assignments("t", _ALL_COURSES)
    b = await client.get_assignments("t", _ALL_COURSES)
    assert a == b


async def test_get_announcements_shape_and_empty():
    from src.domain.entities.announcement import Announcement
    client = FakeMoodleClient()
    anns = await client.get_announcements("t", _ALL_COURSES)
    assert anns and all(isinstance(a, Announcement) for a in anns)
    assert [a.course_id for a in await client.get_announcements("t", [101])] == [101]
    assert await client.get_announcements("t", []) == []


async def test_get_messages_are_received_only_and_deterministic():
    from src.domain.entities.message import Message
    client = FakeMoodleClient()
    msgs = await client.get_messages("t", moodle_user_id=1)
    assert msgs and all(isinstance(m, Message) for m in msgs)
    # Deterministas entre llamadas.
    assert await client.get_messages("t", moodle_user_id=1) == msgs
