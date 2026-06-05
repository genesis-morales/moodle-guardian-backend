from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Assignment:
    id: Optional[int]
    moodle_assignment_id: Optional[int]
    moodle_course_id: int
    name: str
    due_date: Optional[datetime] = None
    allow_submissions_from: Optional[datetime] = None
    cutoff_date: Optional[datetime] = None
    url: Optional[str] = None
    is_visible: bool = True

    def stable_key(self) -> str:
        if self.moodle_assignment_id is not None:
            return f"assignment:{self.moodle_assignment_id}"
        return f"assignment:{self.moodle_course_id}:{self.name.strip().lower()}"