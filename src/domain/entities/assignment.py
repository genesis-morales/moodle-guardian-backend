from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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

    def stable_key(self) -> str:
        if self.moodle_assignment_id is not None:
            return f"assignment:{self.moodle_assignment_id}"
        return f"assignment:{self.moodle_course_id}:{self.name.strip().lower()}"

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