from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional

from src.domain.entities.source_type import SourceType


@dataclass
class Assignment:
    moodle_assignment_id: int
    moodle_course_id: int
    name: str
    due_date: datetime | None = None
    allow_submissions_from: datetime | None = None
    cutoff_date: datetime | None = None
    id: Optional[int] = None
    # Presentation-only: never used in stable_key nor in diff comparison.
    course_name: str | None = None

    source_type: ClassVar[str] = SourceType.ASSIGNMENT

    def stable_key(self) -> str:
        if self.moodle_assignment_id is not None:
            return f"assignment:{self.moodle_assignment_id}"
        return f"assignment:{self.moodle_course_id}:{self.name.strip().lower()}"

    def changed_fields(self, other: "Assignment") -> list[str]:
        """Campos que difieren respecto a una versión previa (para avisar cambios)."""
        changed: list[str] = []
        if self.name != other.name:
            changed.append("name")
        if self.due_date != other.due_date:
            changed.append("due_date")
        if self.allow_submissions_from != other.allow_submissions_from:
            changed.append("allow_submissions_from")
        if self.cutoff_date != other.cutoff_date:
            changed.append("cutoff_date")
        return changed

    def to_dict(self) -> dict:
        return {
            "moodle_assignment_id": self.moodle_assignment_id,
            "moodle_course_id": self.moodle_course_id,
            "name": self.name,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "allow_submissions_from": (
                self.allow_submissions_from.isoformat()
                if self.allow_submissions_from
                else None
            ),
            "cutoff_date": self.cutoff_date.isoformat() if self.cutoff_date else None,
            "course_name": self.course_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Assignment":
        return cls(
            moodle_assignment_id=data["moodle_assignment_id"],
            moodle_course_id=data["moodle_course_id"],
            name=data["name"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            allow_submissions_from=(
                datetime.fromisoformat(data["allow_submissions_from"])
                if data.get("allow_submissions_from")
                else None
            ),
            cutoff_date=datetime.fromisoformat(data["cutoff_date"]) if data.get("cutoff_date") else None,
            course_name=data.get("course_name"),
        )

    def is_past(self, now: datetime) -> bool:
        """True si la tarea ya no es accionable (su último plazo pasó).

        Se considera el plazo más tardío entre `due_date` y `cutoff_date`
        (Moodle permite entregar tarde hasta el cutoff). Una tarea sin ninguna
        fecha se trata como abierta/vigente (no vencida).
        """
        deadline = max(
            (d for d in (self.due_date, self.cutoff_date) if d is not None),
            default=None,
        )
        if deadline is None:
            return False
        return deadline < now