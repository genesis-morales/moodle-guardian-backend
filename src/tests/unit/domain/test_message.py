from datetime import UTC, datetime

from src.domain.entities.message import Message
from src.domain.entities.source_type import SourceType

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


def _msg(**kw) -> Message:
    base = dict(
        message_id=9101,
        sender_name="Prof. X",
        preview="Recordá subir tu avance.",
        sent_at=NOW,
        conversation_id=501,
        sender_id=42,
    )
    base.update(kw)
    return Message(**base)


def test_source_type_and_stable_key():
    assert Message.source_type == SourceType.MESSAGE
    assert _msg().stable_key() == "message:9101"


def test_messages_are_immutable_never_changed():
    # Aunque cambie el texto, un mensaje nunca se reporta como "actualizado".
    assert _msg().changed_fields(_msg(preview="otro texto")) == []


def test_to_dict_does_not_leak_preview():
    """Privacidad (PII): el texto del mensaje NO se persiste."""
    data = _msg().to_dict()
    assert "preview" not in data
    assert data["message_id"] == 9101
    assert data["sender_name"] == "Prof. X"


def test_from_dict_round_trip_drops_preview():
    # El round-trip por persistencia pierde el preview a propósito: el resto se
    # conserva. (El preview solo vive en memoria para la notificación.)
    m = _msg()
    restored = Message.from_dict(m.to_dict())
    assert restored.preview is None
    assert restored == _msg(preview=None)


def test_message_has_no_course_attribute():
    # El contrato excluye 'course' deliberadamente (mensajes son conversaciones).
    assert not hasattr(_msg(), "course_id")
