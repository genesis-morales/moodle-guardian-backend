from datetime import UTC, datetime, timedelta

from src.domain.entities.assignment import Assignment

NOW = datetime(2026, 6, 18, tzinfo=UTC)


def assignment(due=None, cutoff=None) -> Assignment:
    return Assignment(
        moodle_assignment_id=1,
        moodle_course_id=1,
        name="Entrega",
        due_date=due,
        cutoff_date=cutoff,
    )


def test_past_due_without_cutoff_is_past():
    assert assignment(due=NOW - timedelta(days=1)).is_past(NOW) is True


def test_future_due_is_not_past():
    assert assignment(due=NOW + timedelta(days=2)).is_past(NOW) is False


def test_due_past_but_cutoff_future_is_not_past():
    # Se puede entregar tarde hasta el cutoff -> sigue siendo accionable.
    a = assignment(due=NOW - timedelta(days=1), cutoff=NOW + timedelta(days=3))
    assert a.is_past(NOW) is False


def test_without_any_date_is_not_past():
    assert assignment().is_past(NOW) is False
