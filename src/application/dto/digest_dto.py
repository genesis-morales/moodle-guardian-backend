from dataclasses import dataclass
from datetime import datetime


@dataclass
class DeliverableItem:
    """Un entregable con fecha, unificando tareas y eventos para los reportes
    proactivos (digest semanal y recordatorio de 3 días)."""

    name: str
    course_name: str | None
    deadline: datetime
    module: str | None  # "forum"/"quiz"/... para eventos; None para tareas
    kind: str  # "assignment" | "event"
    key: str  # stable_key del entregable, para el historial de notificaciones
