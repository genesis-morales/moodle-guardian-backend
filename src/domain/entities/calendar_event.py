from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CalendarEvent:
    moodle_event_id: int
    course_id: int
    name: str
    event_type: str
    due_date: datetime | None = None
    url: str | None = None
    id: Optional[int] = None
    # Presentation-only: never used in stable_key nor in diff comparison.
    course_name: str | None = None

    def stable_key(self) -> str:
        if self.moodle_event_id is not None:
            return f"event:{self.moodle_event_id}"
        course_part = self.course_id if self.course_id is not None else "global"
        return f"event:{course_part}:{self.name.strip().lower()}"