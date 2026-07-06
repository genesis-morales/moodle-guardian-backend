from datetime import UTC, datetime
from typing import Callable, Optional

from src.domain.entities.diff_result import (
    ChangedAssignment,
    ChangedEvent,
    ChangedInstruction,
    DiffResult,
)
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.trackable_item import TrackableItem


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

        # Tareas y eventos: un removido cuyo plazo ya pasó simplemente caducó
        # (no lo borró el profe) -> se silencia vía is_past.
        a_new, a_upd, a_rem = self._diff_source(
            previous.assignments,
            current.assignments,
            changed_cls=ChangedAssignment,
            silence_removed=lambda item: item.is_past(now),
        )
        e_new, e_upd, e_rem = self._diff_source(
            previous.events,
            current.events,
            changed_cls=ChangedEvent,
            silence_removed=lambda item: item.is_past(now),
        )
        # Instrucciones (PDFs): sin filtro por fecha, pero se suprimen por completo
        # (new/updated/removed) las que un entregable del mismo curso ya absorbe.
        i_new, i_upd, i_rem = self._diff_source(
            previous.instructions,
            current.instructions,
            changed_cls=ChangedInstruction,
            suppress=lambda item: self._is_superseded(item, current),
        )

        return DiffResult(
            new_assignments=a_new,
            updated_assignments=a_upd,
            removed_assignments=a_rem,
            new_events=e_new,
            updated_events=e_upd,
            removed_events=e_rem,
            new_instructions=i_new,
            updated_instructions=i_upd,
            removed_instructions=i_rem,
        )

    def _diff_source(
        self,
        previous_items: list,
        current_items: list,
        *,
        changed_cls: type,
        suppress: Optional[Callable[[TrackableItem], bool]] = None,
        silence_removed: Optional[Callable[[TrackableItem], bool]] = None,
    ) -> tuple[list, list, list]:
        """Diff genérico de una fuente por `stable_key()`.

        - `suppress`: si devuelve True para un ítem, este NO se reporta en ninguna
          categoría (new/updated/removed). Es la absorción de instrucciones.
        - `silence_removed`: si devuelve True para un ítem que desapareció, no se
          reporta como removido (p. ej. venció y se cayó del calendario).

        Reemplaza las tripletas `_find_new/_updated/_removed_*` + los `_*_map` que
        antes se copiaban por tipo. Agregar una fuente nueva = una llamada más.
        """
        previous_map = {item.stable_key(): item for item in previous_items}
        current_map = {item.stable_key(): item for item in current_items}

        new = [
            item
            for key, item in current_map.items()
            if key not in previous_map and not (suppress and suppress(item))
        ]

        updated = []
        for key, current_item in current_map.items():
            previous_item = previous_map.get(key)
            if previous_item is None:
                continue
            if suppress and suppress(current_item):
                continue
            fields = current_item.changed_fields(previous_item)
            if fields:
                updated.append(
                    changed_cls(
                        previous=previous_item,
                        current=current_item,
                        changed_fields=fields,
                    )
                )

        removed = []
        for key, item in previous_map.items():
            if key in current_map:
                continue
            if suppress and suppress(item):
                continue
            if silence_removed and silence_removed(item):
                continue
            removed.append(item)

        return new, updated, removed

    def _is_superseded(self, instruction, current: Snapshot) -> bool:
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
