from datetime import datetime
from typing import Protocol

# Tipos de notificación registrados en el historial.
NOTIFICATION_REMINDER = "reminder"
NOTIFICATION_WEEKLY_DIGEST = "weekly_digest"


class SentReminderRepository(Protocol):
    async def latest_deadlines(
        self, user_id: int, notification_type: str
    ) -> dict[str, datetime | None]:
        """Para cada deliverable_key ya notificado a este usuario de este tipo,
        devuelve el `deadline_snapshot` del envío más reciente. Permite saber qué
        ya se avisó y detectar cambios de fecha (re-notificar)."""
        ...

    async def record(
        self,
        user_id: int,
        notification_type: str,
        deliverable_key: str | None,
        deadline_snapshot: datetime | None,
    ) -> None:
        """Registra un envío en el historial."""
        ...
