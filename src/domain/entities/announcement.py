from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional

from src.domain.entities.source_type import SourceType


@dataclass
class Announcement:
    """Anuncio del foro de Novedades/News de un curso (mod_forum).

    Cada anuncio es una *discussion* del foro tipo `news`. La identidad estable es
    el `discussion_id`; `content_fingerprint` (derivado del `timemodified` de la
    discusión) permite detectar que el profe editó el anuncio sin comparar el
    cuerpo completo. Sigue el mismo patrón que Instruction/CalendarEvent.

    Es una fuente **con curso**: se agrupa bajo su curso en la notificación (o en
    "Avisos Generales" si no se resolvió el nombre). No tiene ventana temporal (un
    anuncio no "vence"); el diff contra el snapshot previo decide qué es nuevo.
    """

    discussion_id: int          # identidad estable (id de la discusión)
    course_id: int
    name: str                   # asunto del anuncio
    content_fingerprint: str | None = None  # str(timemodified) — detecta edición
    url: str | None = None
    author: str | None = None
    posted_at: datetime | None = None
    id: Optional[int] = None
    # Presentation-only: never used in stable_key nor in diff comparison.
    course_name: str | None = None

    source_type: ClassVar[str] = SourceType.ANNOUNCEMENT

    def stable_key(self) -> str:
        return f"announcement:{self.discussion_id}"

    def changed_fields(self, other: "Announcement") -> list[str]:
        """Cambios relevantes de un anuncio: su asunto o su contenido (via la
        huella derivada del timemodified). No desglosa el cuerpo."""
        changed: list[str] = []
        if self.name != other.name:
            changed.append("name")
        if self.content_fingerprint != other.content_fingerprint:
            changed.append("content")
        return changed

    def to_dict(self) -> dict:
        return {
            "discussion_id": self.discussion_id,
            "course_id": self.course_id,
            "name": self.name,
            "content_fingerprint": self.content_fingerprint,
            "url": self.url,
            "author": self.author,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "course_name": self.course_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Announcement":
        return cls(
            discussion_id=data["discussion_id"],
            course_id=data["course_id"],
            name=data["name"],
            content_fingerprint=data.get("content_fingerprint"),
            url=data.get("url"),
            author=data.get("author"),
            posted_at=datetime.fromisoformat(data["posted_at"]) if data.get("posted_at") else None,
            course_name=data.get("course_name"),
        )
