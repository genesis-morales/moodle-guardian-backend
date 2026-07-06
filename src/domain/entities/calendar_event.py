from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, Optional

from src.domain.entities.source_type import SourceType


@dataclass
class CalendarEvent:
    moodle_event_id: int
    course_id: int
    name: str
    event_type: str
    due_date: datetime | None = None
    url: str | None = None
    id: Optional[int] = None
    # Módulo de Moodle de origen ("forum", "quiz", "assign", "scorm"...).
    # None para eventos personales/de sitio (eventtype="user"). Solo se usa para
    # la etiqueta de presentación; no entra en stable_key ni en el diff.
    module: str | None = None
    # Presentation-only: never used in stable_key nor in diff comparison.
    course_name: str | None = None

    source_type: ClassVar[str] = SourceType.EVENT

    def stable_key(self) -> str:
        if self.moodle_event_id is not None:
            return f"event:{self.moodle_event_id}"
        course_part = self.course_id if self.course_id is not None else "global"
        return f"event:{course_part}:{self.name.strip().lower()}"

    def is_past(self, now: datetime) -> bool:
        """True si el evento ya venció (su fecha quedó atrás).

        Un evento con fecha pasada que desaparece simplemente caducó y se cayó de
        la ventana del calendario: no es noticia. Uno sin fecha (o futuro) que
        desaparece sí se avisa (lo borró/movió el profe). Coincide con la lógica
        que antes vivía inline en DiffService. Coerciona naive->UTC por defensa."""
        if self.due_date is None:
            return False
        due = self.due_date if self.due_date.tzinfo else self.due_date.replace(tzinfo=UTC)
        return due < now

    def changed_fields(self, other: "CalendarEvent") -> list[str]:
        changed: list[str] = []
        if self.name != other.name:
            changed.append("name")
        if self.event_type != other.event_type:
            changed.append("event_type")
        if self.due_date != other.due_date:
            changed.append("due_date")
        if self.url != other.url:
            changed.append("url")
        return changed

    def to_dict(self) -> dict:
        return {
            "moodle_event_id": self.moodle_event_id,
            "course_id": self.course_id,
            "name": self.name,
            "event_type": self.event_type,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "url": self.url,
            "module": self.module,
            "course_name": self.course_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalendarEvent":
        return cls(
            moodle_event_id=data["moodle_event_id"],
            course_id=data["course_id"],
            name=data["name"],
            event_type=data["event_type"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            url=data.get("url"),
            module=data.get("module"),
            course_name=data.get("course_name"),
        )