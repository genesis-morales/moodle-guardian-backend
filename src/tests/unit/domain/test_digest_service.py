from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.services import digest_service

CR = ZoneInfo("America/Costa_Rica")  # UTC-6
NOW = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)


def assignment(name, due=None, cutoff=None) -> Assignment:
    return Assignment(
        moodle_assignment_id=1,
        moodle_course_id=1,
        name=name,
        due_date=due,
        cutoff_date=cutoff,
    )


def event(name, due, module=None) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=1,
        course_id=1,
        name=name,
        event_type="due",
        due_date=due,
        module=module,
    )


def test_collect_sorts_by_deadline_and_uses_latest_assignment_date():
    a = assignment(
        "Tarea",
        due=datetime(2026, 6, 25, 5, 59, tzinfo=UTC),
        cutoff=datetime(2026, 6, 27, 5, 59, tzinfo=UTC),
    )
    e = event("Foro", datetime(2026, 6, 24, 5, 59, tzinfo=UTC), module="forum")

    items = digest_service.collect_deliverables([a], [e])

    # Orden cronológico: foro (24) antes que tarea (27, el cutoff).
    assert [i.name for i in items] == ["Foro", "Tarea"]
    tarea = next(i for i in items if i.name == "Tarea")
    assert tarea.deadline == datetime(2026, 6, 27, 5, 59, tzinfo=UTC)


def test_collect_drops_items_without_date():
    assert digest_service.collect_deliverables([assignment("Sin fecha")], []) == []


def test_filter_future():
    items = digest_service.collect_deliverables(
        [],
        [
            event("Pasado", NOW - timedelta(days=1)),
            event("Futuro", NOW + timedelta(days=1)),
        ],
    )
    res = digest_service.filter_future(items, NOW)
    assert [i.name for i in res] == ["Futuro"]


def test_collect_sets_stable_key():
    items = digest_service.collect_deliverables(
        [], [event("Foro", datetime(2026, 6, 24, 5, 59, tzinfo=UTC), module="forum")]
    )
    assert items[0].key == "event:1"  # stable_key del evento con moodle_event_id=1


def test_filter_due_within_includes_window_and_excludes_past():
    items = digest_service.collect_deliverables(
        [],
        [
            event("Vencido", NOW - timedelta(days=1)),
            event("En 2 dias", NOW + timedelta(days=2)),
            event("En 5 dias", NOW + timedelta(days=5)),
        ],
    )
    # Ventana de 3 dias: entra "En 2 dias", quedan fuera el vencido y el de 5.
    res = digest_service.filter_due_within(items, NOW, 3, CR)
    assert [i.name for i in res] == ["En 2 dias"]


def test_filter_due_on_local_date_respects_timezone():
    # 2026-06-26 05:59 UTC == 2026-06-25 23:59 hora local (CR, UTC-6).
    items = digest_service.collect_deliverables(
        [], [event("Entrega", datetime(2026, 6, 26, 5, 59, tzinfo=UTC), module="assign")]
    )

    # Debe matchear la fecha LOCAL (25), no la UTC (26).
    assert digest_service.filter_due_on_local_date(items, date(2026, 6, 25), CR)
    assert not digest_service.filter_due_on_local_date(items, date(2026, 6, 26), CR)
