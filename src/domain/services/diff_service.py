from datetime import UTC, datetime

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.diff_result import (
    ChangedAssignment,
    ChangedEvent,
    ChangedInstruction,
    DiffResult,
)
from src.domain.entities.snapshot import Snapshot


class DiffService:
    def compare(
        self,
        previous: Snapshot | None,
        current: Snapshot,
        now: datetime | None = None,
    ) -> DiffResult:
        if previous is None:
            return DiffResult()

        if now is None:
            now = datetime.now(UTC)

        return DiffResult(
            new_assignments=self._find_new_assignments(previous, current),
            updated_assignments=self._find_updated_assignments(previous, current),
            removed_assignments=self._find_removed_assignments(previous, current, now),
            new_events=self._find_new_events(previous, current),
            updated_events=self._find_updated_events(previous, current),
            removed_events=self._find_removed_events(previous, current, now),
            new_instructions=self._find_new_instructions(previous, current),
            updated_instructions=self._find_updated_instructions(previous, current),
            removed_instructions=self._find_removed_instructions(previous, current),
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
        now: datetime,
    ) -> list[Assignment]:
        previous_map = self._assignment_map(previous.assignments)
        current_map = self._assignment_map(current.assignments)

        removed: list[Assignment] = []
        for key, assignment in previous_map.items():
            if key in current_map:
                continue
            # Igual que con los eventos: si la tarea ya venció, simplemente
            # caducó (no es que el profe la borrara). La silenciamos.
            if assignment.is_past(now):
                continue
            removed.append(assignment)

        return removed

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

    def _find_new_instructions(self, previous: Snapshot, current: Snapshot) -> list[Instruction]:
        previous_map = self._instruction_map(previous.instructions)
        current_map = self._instruction_map(current.instructions)
        return [
            instruction
            for key, instruction in current_map.items()
            if key not in previous_map
            and not self._is_superseded(instruction, current)
        ]

    def _find_updated_instructions(
        self,
        previous: Snapshot,
        current: Snapshot,
    ) -> list[ChangedInstruction]:
        previous_map = self._instruction_map(previous.instructions)
        current_map = self._instruction_map(current.instructions)

        changes: list[ChangedInstruction] = []

        for key, current_instruction in current_map.items():
            previous_instruction = previous_map.get(key)
            if previous_instruction is None:
                continue

            # Si el espacio de entrega ya absorbió este PDF, sus cambios de
            # contenido tampoco son noticia aparte: el Assignment manda.
            if self._is_superseded(current_instruction, current):
                continue

            # El único cambio relevante (sin descargar el PDF) es la huella de
            # contenido, derivada del timemodified de Moodle.
            if previous_instruction.content_fingerprint != current_instruction.content_fingerprint:
                changes.append(
                    ChangedInstruction(
                        previous=previous_instruction,
                        current=current_instruction,
                        changed_fields=["content"],
                    )
                )

        return changes

    def _find_removed_instructions(self, previous: Snapshot, current: Snapshot) -> list[Instruction]:
        previous_map = self._instruction_map(previous.instructions)
        current_map = self._instruction_map(current.instructions)
        return [
            instruction
            for key, instruction in previous_map.items()
            if key not in current_map
            # No avisamos "🔴 [Instrucción]" cuando el PDF desaparece pero su
            # espacio de entrega ya existe: no lo borraron, lo reemplazó la tarea.
            and not self._is_superseded(instruction, current)
        ]

    def _is_superseded(self, instruction: Instruction, current: Snapshot) -> bool:
        """True si algún espacio de entrega del mismo curso absorbe esta
        instrucción (su nombre está contenido, por tokens, en el del PDF).

        Se empareja contra `deliverable_refs`, que contiene TODOS los entregables
        del curso (tareas y foros) SIN filtrar por fecha. Así una instrucción
        queda absorbida aunque su entregable ya haya vencido y, por tanto, no
        aparezca en `assignments`/`events` (que sí se filtran)."""
        return any(
            ref.course_id == instruction.course_id
            and instruction.is_superseded_by(ref.name)
            for ref in current.deliverable_refs
        )

    def _find_removed_events(
        self,
        previous: Snapshot,
        current: Snapshot,
        now: datetime,
    ) -> list[CalendarEvent]:
        previous_map = self._event_map(previous.events)
        current_map = self._event_map(current.events)

        removed: list[CalendarEvent] = []
        for key, event in previous_map.items():
            if key in current_map:
                continue
            # Un evento "removido" cuya fecha ya pasó simplemente caducó y se
            # cayó de la ventana del calendario: no es noticia, lo silenciamos.
            # Si la fecha sigue en el futuro (o no tiene fecha) sí avisamos,
            # porque significa que el profe lo borró/movió.
            if event.due_date is not None and self._as_utc(event.due_date) < now:
                continue
            removed.append(event)

        return removed

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _assignment_map(self, assignments: list[Assignment]) -> dict[str, Assignment]:
        return {assignment.stable_key(): assignment for assignment in assignments}

    def _event_map(self, events: list[CalendarEvent]) -> dict[str, CalendarEvent]:
        return {event.stable_key(): event for event in events}

    def _instruction_map(self, instructions: list[Instruction]) -> dict[str, Instruction]:
        return {instruction.stable_key(): instruction for instruction in instructions}

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