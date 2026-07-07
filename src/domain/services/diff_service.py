from datetime import UTC, datetime
from typing import Callable, Optional

from src.domain.entities.diff_result import Change, DiffResult, SourceChanges
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.source_type import SourceType
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

        # Política de diff por fuente. Cada fuente declara cómo tratar sus casos
        # borde; agregar una fuente nueva = una entrada aquí (o el default si no
        # necesita nada especial).
        #   - suppress: no reportar el ítem en ninguna categoría (absorción).
        #   - silence_removed: no avisar cuando el ítem desaparece.
        def is_past(item: TrackableItem) -> bool:
            return getattr(item, "is_past", lambda _n: False)(now)

        def always(_item: TrackableItem) -> bool:
            return True

        policies: dict[str, dict[str, Callable[[TrackableItem], bool]]] = {
            # Tareas/eventos: un removido cuyo plazo ya pasó simplemente caducó.
            SourceType.ASSIGNMENT: {"silence_removed": is_past},
            SourceType.EVENT: {"silence_removed": is_past},
            # Instrucciones (PDFs): se suprimen por completo las que un entregable
            # del mismo curso ya absorbe. Las que sobreviven son huérfanas (sin
            # espacio de entrega que las cubra) y, como no tienen fecha, no
            # podemos saber si una edición posterior es de algo vigente o ya
            # vencido: se avisan UNA vez (new) y no se re-notifican al cambiar
            # contenido (silence_updated).
            SourceType.INSTRUCTION: {
                "suppress": lambda item: self._is_superseded(item, current),
                "silence_updated": always,
            },
            # Anuncios/mensajes: nunca avisamos "desapareció" (un anuncio retirado
            # o un mensaje ya no listado es ruido, no señal).
            SourceType.ANNOUNCEMENT: {"silence_removed": always},
            SourceType.MESSAGE: {"silence_removed": always},
        }

        # Recorremos todas las fuentes presentes en cualquiera de los dos snapshots.
        source_types = set(previous.items) | set(current.items)
        changes: dict[str, SourceChanges] = {}
        for source_type in source_types:
            policy = policies.get(source_type, {})
            bucket = self._diff_source(
                previous.items_of(source_type),
                current.items_of(source_type),
                suppress=policy.get("suppress"),
                silence_removed=policy.get("silence_removed"),
                silence_updated=policy.get("silence_updated"),
            )
            if bucket.has_changes:
                changes[source_type] = bucket

        return DiffResult(changes=changes)

    def _diff_source(
        self,
        previous_items: list,
        current_items: list,
        *,
        suppress: Optional[Callable[[TrackableItem], bool]] = None,
        silence_removed: Optional[Callable[[TrackableItem], bool]] = None,
        silence_updated: Optional[Callable[[TrackableItem], bool]] = None,
    ) -> SourceChanges:
        """Diff genérico de una fuente por `stable_key()`.

        - `suppress`: si devuelve True para un ítem, este NO se reporta en ninguna
          categoría (new/updated/removed). Es la absorción de instrucciones.
        - `silence_removed`: si devuelve True para un ítem que desapareció, no se
          reporta como removido (p. ej. venció y se cayó del calendario).
        - `silence_updated`: si devuelve True para un ítem que cambió, no se
          reporta como actualizado (se avisa la primera vez y luego calla).

        Agregar una fuente nueva = una llamada más (o una entrada en el mapa de
        políticas de `compare`).
        """
        previous_map = {item.stable_key(): item for item in previous_items}
        current_map = {item.stable_key(): item for item in current_items}

        new = [
            item
            for key, item in current_map.items()
            if key not in previous_map and not (suppress and suppress(item))
        ]

        updated: list[Change] = []
        for key, current_item in current_map.items():
            previous_item = previous_map.get(key)
            if previous_item is None:
                continue
            if suppress and suppress(current_item):
                continue
            if silence_updated and silence_updated(current_item):
                continue
            fields = current_item.changed_fields(previous_item)
            if fields:
                updated.append(
                    Change(
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

        return SourceChanges(new=new, updated=updated, removed=removed)

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
