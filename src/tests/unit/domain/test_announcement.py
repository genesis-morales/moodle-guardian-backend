from datetime import UTC, datetime

from src.domain.entities.announcement import Announcement
from src.domain.entities.source_type import SourceType

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


def _ann(**kw) -> Announcement:
    base = dict(
        discussion_id=8001,
        course_id=101,
        name="Bienvenida",
        content_fingerprint="1700000000",
        author="Prof. X",
        posted_at=NOW,
        course_name="Programación",
    )
    base.update(kw)
    return Announcement(**base)


def test_source_type_and_stable_key():
    assert Announcement.source_type == SourceType.ANNOUNCEMENT
    assert _ann().stable_key() == "announcement:8001"


def test_changed_fields_detects_subject_and_content():
    a = _ann()
    assert a.changed_fields(_ann()) == []
    assert a.changed_fields(_ann(name="Otro asunto")) == ["name"]
    assert a.changed_fields(_ann(content_fingerprint="1700000999")) == ["content"]
    both = a.changed_fields(_ann(name="X", content_fingerprint="9"))
    assert set(both) == {"name", "content"}


def test_dict_round_trip():
    a = _ann()
    assert Announcement.from_dict(a.to_dict()) == a


def test_round_trip_without_optional_fields():
    a = Announcement(discussion_id=1, course_id=2, name="Sin extras")
    assert Announcement.from_dict(a.to_dict()) == a
