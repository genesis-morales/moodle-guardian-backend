from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.source_type import SourceType
from src.domain.entities.trackable_item import TrackableItem


@dataclass(frozen=True)
class DeliverableRef:
    """Referencia ligera a un entregable (tarea o foro) para absorber
    instrucciones.

    A diferencia de `assignments`/`events` (que se filtran por fecha antes de
    notificar), aquí van TODOS los entregables del curso SIN filtrar: una
    instrucción debe quedar absorbida aunque su entregable ya haya vencido o
    quede fuera de la ventana de notificación. Campo transitorio del snapshot
    recién capturado; no se persiste."""

    course_id: int
    name: str


class Snapshot:
    """Foto de las fuentes rastreables de un usuario en un instante.

    Almacena los ítems genéricamente en `items: {source_type: [TrackableItem]}`,
    para que agregar una fuente nueva no exija un campo nuevo. Se mantienen las
    propiedades `assignments`/`events`/`instructions` por compatibilidad con el
    código existente (diff, mapeo DTO, notificación). El constructor acepta tanto
    los kwargs legacy por tipo como un `items` genérico.
    """

    def __init__(
        self,
        user_id: Optional[int],
        moodle_user_id: int,
        captured_at: datetime,
        assignments: Optional[List[Assignment]] = None,
        events: Optional[List[CalendarEvent]] = None,
        instructions: Optional[List[Instruction]] = None,
        deliverable_refs: Optional[List[DeliverableRef]] = None,
        items: Optional[dict[str, List[TrackableItem]]] = None,
    ) -> None:
        self.user_id = user_id
        self.moodle_user_id = moodle_user_id
        self.captured_at = captured_at
        self.deliverable_refs: List[DeliverableRef] = list(deliverable_refs or [])

        self.items: dict[str, List[TrackableItem]] = {}
        if items:
            self.items = {k: list(v) for k, v in items.items()}
        # Los kwargs legacy por tipo se pliegan sobre `items` (fuente de verdad).
        if assignments:
            self.items.setdefault(SourceType.ASSIGNMENT, []).extend(assignments)
        if events:
            self.items.setdefault(SourceType.EVENT, []).extend(events)
        if instructions:
            self.items.setdefault(SourceType.INSTRUCTION, []).extend(instructions)

    def items_of(self, source_type: str) -> List[TrackableItem]:
        return self.items.get(source_type, [])

    @property
    def assignments(self) -> List[Assignment]:
        return self.items.get(SourceType.ASSIGNMENT, [])

    @property
    def events(self) -> List[CalendarEvent]:
        return self.items.get(SourceType.EVENT, [])

    @property
    def instructions(self) -> List[Instruction]:
        return self.items.get(SourceType.INSTRUCTION, [])

    def is_empty(self) -> bool:
        return not any(self.items.values())
