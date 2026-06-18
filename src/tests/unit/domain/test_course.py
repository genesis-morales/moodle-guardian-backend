from datetime import UTC, datetime, timedelta

from src.domain.entities.course import Course

NOW = datetime(2026, 6, 18, tzinfo=UTC)


def course(end_date: datetime | None) -> Course:
    return Course(
        id=None,
        moodle_course_id=1,
        fullname="Curso",
        shortname="C - IIC2026",
        end_date=end_date,
    )


def test_course_with_past_enddate_is_inactive():
    assert course(NOW - timedelta(days=1)).is_active(NOW) is False


def test_course_with_future_enddate_is_active():
    assert course(NOW + timedelta(days=30)).is_active(NOW) is True


def test_course_without_enddate_is_active():
    # Moodle entrega enddate=0 (-> None) para cursos sin cierre: se mantienen.
    assert course(None).is_active(NOW) is True


def test_course_ending_exactly_now_is_active():
    assert course(NOW).is_active(NOW) is True
