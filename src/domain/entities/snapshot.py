from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent


@dataclass
class Snapshot:
    user_id: Optional[int]
    moodle_user_id: int
    captured_at: datetime

    assignments: List[Assignment] = field(default_factory=list)
    events: List[CalendarEvent] = field(default_factory=list)

    # futuro
    forum_posts: List["ForumPost"] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([
            self.assignments,
            self.events,
            self.forum_posts,
        ])