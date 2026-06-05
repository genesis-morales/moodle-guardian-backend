from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CalendarEvent:
    id: Optional[int]
    moodle_event_id: Optional[int]
    course_id: Optional[int]
    name: str
    event_type: Optional[str] = None
    due_date: Optional[datetime] = None
    url: Optional[str] = None

    def stable_key(self) -> str:
        if self.moodle_event_id is not None:
            return f"event:{self.moodle_event_id}"
        course_part = self.course_id if self.course_id is not None else "global"
        return f"event:{course_part}:{self.name.strip().lower()}"