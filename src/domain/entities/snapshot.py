from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction


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


@dataclass
class Snapshot:
    user_id: Optional[int]
    moodle_user_id: int
    captured_at: datetime

    assignments: List[Assignment] = field(default_factory=list)
    events: List[CalendarEvent] = field(default_factory=list)
    instructions: List[Instruction] = field(default_factory=list)
    deliverable_refs: List[DeliverableRef] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([
            self.assignments,
            self.events,
            self.instructions,
        ])
