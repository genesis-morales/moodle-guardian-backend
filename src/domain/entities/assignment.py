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

    def stable_key(self) -> str:
        if self.moodle_assignment_id is not None:
            return f"assignment:{self.moodle_assignment_id}"
        return f"assignment:{self.moodle_course_id}:{self.name.strip().lower()}"