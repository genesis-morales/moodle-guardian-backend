from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent


@dataclass
class Snapshot:
    user_id: int
    course_id: int
    captured_at: datetime
    assignments: List[Assignment] = field(default_factory=list)
    events: List[CalendarEvent] = field(default_factory=list)
    raw_hash: str | None = None