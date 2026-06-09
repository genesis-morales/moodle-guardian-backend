from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.diff_result import (
    ChangedAssignment,
    ChangedEvent,
    DiffResult,
)
from src.domain.entities.snapshot import Snapshot


class DiffService:
    def compare(self, previous: Snapshot | None, current: Snapshot) -> DiffResult:
        if previous is None:
            return DiffResult()

        return DiffResult(
            new_assignments=self._find_new_assignments(previous, current),
            updated_assignments=self._find_updated_assignments(previous, current),
            removed_assignments=self._find_removed_assignments(previous, current),
            new_events=self._find_new_events(previous, current),
            updated_events=self._find_updated_events(previous, current),
            removed_events=self._find_removed_events(previous, current),
        )

    def _find_new_assignments(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[Assignment]:
        previous_map = self._assignment_map(previous.assignments)
        current_map = self._assignment_map(current.assignments)

        return [
            assignment
            for key, assignment in current_map.items()
            if key not in previous_map
        ]

    def _find_updated_assignments(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[ChangedAssignment]:
        previous_map = self._assignment_map(previous.assignments)
        current_map = self._assignment_map(current.assignments)

        changes: list[ChangedAssignment] = []

        for key, current_assignment in current_map.items():
            previous_assignment = previous_map.get(key)
            if previous_assignment is None:
                continue

            changed_fields = self._compare_assignment_fields(
                previous_assignment,
                current_assignment,
            )

            if changed_fields:
                changes.append(
                    ChangedAssignment(
                        previous=previous_assignment,
                        current=current_assignment,
                        changed_fields=changed_fields,
                    )
                )

        return changes

    def _find_removed_assignments(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[Assignment]:
        previous_map = self._assignment_map(previous.assignments)
        current_map = self._assignment_map(current.assignments)

        return [
            assignment
            for key, assignment in previous_map.items()
            if key not in current_map
        ]

    def _find_new_events(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[CalendarEvent]:
        previous_map = self._event_map(previous.events)
        current_map = self._event_map(current.events)

        return [
            event
            for key, event in current_map.items()
            if key not in previous_map
        ]

    def _find_updated_events(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[ChangedEvent]:
        previous_map = self._event_map(previous.events)
        current_map = self._event_map(current.events)

        changes: list[ChangedEvent] = []

        for key, current_event in current_map.items():
            previous_event = previous_map.get(key)
            if previous_event is None:
                continue

            changed_fields = self._compare_event_fields(
                previous_event,
                current_event,
            )

            if changed_fields:
                changes.append(
                    ChangedEvent(
                        previous=previous_event,
                        current=current_event,
                        changed_fields=changed_fields,
                    )
                )

        return changes

    def _find_removed_events(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[CalendarEvent]:
        previous_map = self._event_map(previous.events)
        current_map = self._event_map(current.events)

        return [
            event
            for key, event in previous_map.items()
            if key not in current_map
        ]

    def _assignment_map(self, assignments: list[Assignment]) -> dict[str, Assignment]:
        return {assignment.stable_key(): assignment for assignment in assignments}

    def _event_map(self, events: list[CalendarEvent]) -> dict[str, CalendarEvent]:
        return {event.stable_key(): event for event in events}

    def _compare_assignment_fields(self, previous: Assignment, current: Assignment,) -> list[str]:
        changed_fields: list[str] = []

        if previous.name != current.name:
            changed_fields.append("name")

        if previous.due_date != current.due_date:
            changed_fields.append("due_date")

        if previous.allow_submissions_from != current.allow_submissions_from:
            changed_fields.append("allow_submissions_from")

        if previous.cutoff_date != current.cutoff_date:
            changed_fields.append("cutoff_date")

        return changed_fields

    def _compare_event_fields(
        self,
        previous: CalendarEvent,
        current: CalendarEvent,
    ) -> list[str]:
        changed_fields: list[str] = []

        if previous.name != current.name:
            changed_fields.append("name")

        if previous.event_type != current.event_type:
            changed_fields.append("event_type")

        if previous.due_date != current.due_date:
            changed_fields.append("due_date")

        if previous.url != current.url:
            changed_fields.append("url")

        return changed_fields