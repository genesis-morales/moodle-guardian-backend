from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional

from src.domain.entities.source_type import SourceType


@dataclass
class Message:
    """Mensaje privado recibido en Moodle (core_message).

    A diferencia del resto de fuentes, un mensaje **no tiene curso**: es una
    conversación entre personas. Por eso el contrato `TrackableItem` no asume
    `course` y el message builder lo agrupa en su propia sección (por remitente),
    no por curso.

    Los mensajes son **inmutables**: `changed_fields` siempre devuelve `[]` (nunca
    se "actualizan"); solo importa detectar los nuevos. La identidad estable es el
    `message_id`.

    Privacidad (PII): el `preview` (texto del mensaje) vive **solo en memoria** para
    construir la notificación; `to_dict()` NO lo persiste. El snapshot guardado solo
    retiene identidad/metadatos (id, remitente, fecha), que es lo único que el
    próximo diff necesita como baseline. Así no dejamos cuerpos de mensajes en la DB.
    """

    message_id: int             # identidad estable
    sender_name: str
    preview: str | None = None  # texto; transitorio, NO se persiste (ver docstring)
    sent_at: datetime | None = None
    conversation_id: int | None = None
    sender_id: int | None = None
    url: str | None = None
    id: Optional[int] = None

    source_type: ClassVar[str] = SourceType.MESSAGE

    def stable_key(self) -> str:
        return f"message:{self.message_id}"

    def changed_fields(self, other: "Message") -> list[str]:
        # Los mensajes no se editan: nunca hay "actualización" que avisar.
        return []

    def to_dict(self) -> dict:
        # NO se serializa `preview`: minimización de PII en la persistencia. El
        # baseline del diff solo necesita la identidad y algo de metadato.
        return {
            "message_id": self.message_id,
            "sender_name": self.sender_name,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            message_id=data["message_id"],
            sender_name=data.get("sender_name", ""),
            preview=data.get("preview"),  # ausente en filas persistidas (por diseño)
            sent_at=datetime.fromisoformat(data["sent_at"]) if data.get("sent_at") else None,
            conversation_id=data.get("conversation_id"),
            sender_id=data.get("sender_id"),
            url=data.get("url"),
        )
