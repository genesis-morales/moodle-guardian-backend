from datetime import UTC, datetime, timedelta

from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.snapshot import Snapshot
from src.domain.services.diff_service import DiffService

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


def event(event_id: int, name: str, due_date: datetime | None) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=event_id,
        course_id=9621,
        name=name,
        event_type="due",
        due_date=due_date,
        module="forum",
    )


def snapshot(events: list[CalendarEvent]) -> Snapshot:
    return Snapshot(
        user_id=1,
        moodle_user_id=1,
        captured_at=NOW,
        assignments=[],
        events=events,
    )


def test_removed_event_already_expired_is_silenced():
    expired = event(1, "Foro vencido", NOW - timedelta(days=1))
    previous = snapshot([expired])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.removed_events == []


def test_removed_event_still_future_is_reported():
    # Desapareció pero su fecha sigue en el futuro -> lo borró el profe: avisar.
    future = event(2, "Entrega futura borrada", NOW + timedelta(days=10))
    previous = snapshot([future])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.removed_events] == ["Entrega futura borrada"]


def test_removed_event_without_date_is_reported():
    no_date = event(3, "Evento sin fecha", None)
    previous = snapshot([no_date])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.removed_events] == ["Evento sin fecha"]


def test_new_event_is_detected():
    nuevo = event(4, "Foro nuevo", NOW + timedelta(days=5))
    previous = snapshot([])
    current = snapshot([nuevo])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.new_events] == ["Foro nuevo"]
