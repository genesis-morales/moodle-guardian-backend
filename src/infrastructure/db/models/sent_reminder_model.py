from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.database import Base


class SentReminderModel(Base):
    """Historial de notificaciones enviadas (no solo un lock anti-duplicados).

    Permite: evitar reenvíos del mismo recordatorio, re-notificar cuando cambia
    la fecha de una entrega (comparando `deadline_snapshot`), y auditar qué se
    envió y cuándo. Sirve para recordatorios, digest y futuros tipos.
    """

    __tablename__ = "sent_reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # stable_key del entregable. Null para notificaciones a nivel usuario (digest).
    deliverable_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # "reminder", "weekly_digest", ... (ver constantes en el puerto del repositorio).
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    # Fecha de la entrega en el momento de notificar; si luego cambia, re-notificamos.
    deadline_snapshot: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
