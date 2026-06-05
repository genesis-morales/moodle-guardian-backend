from dataclasses import dataclass, field
from typing import List

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent


@dataclass
class ChangedAssignment:
    previous: Assignment
    current: Assignment
    changed_fields: List[str] = field(default_factory=list)


@dataclass
class ChangedEvent:
    previous: CalendarEvent
    current: CalendarEvent
    changed_fields: List[str] = field(default_factory=list)


@dataclass
class DiffResult:
    new_assignments: List[Assignment] = field(default_factory=list)
    updated_assignments: List[ChangedAssignment] = field(default_factory=list)
    removed_assignments: List[Assignment] = field(default_factory=list)

    new_events: List[CalendarEvent] = field(default_factory=list)
    updated_events: List[ChangedEvent] = field(default_factory=list)
    removed_events: List[CalendarEvent] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any([
            self.new_assignments,
            self.updated_assignments,
            self.removed_assignments,
            self.new_events,
            self.updated_events,
            self.removed_events,
        ])