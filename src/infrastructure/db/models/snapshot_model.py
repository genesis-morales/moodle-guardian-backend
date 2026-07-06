from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.database import Base


class SnapshotModel(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Multi-campus: el snapshot pertenece a una conexión (campus). Nullable por las
    # filas pre-multi-campus (backfilleadas a la conexión aprende de la cuenta).
    connection_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("moodle_connections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    moodle_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    # Almacén genérico de fuentes rastreables: {source_type: [item_dict, ...]}.
    # Reemplaza a las columnas por-tipo de abajo (que se conservan una release por
    # seguridad de rollback y para leer filas pre-migración). Agregar una fuente
    # nueva NO requiere cambiar el esquema.
    items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    # Legacy (assignments/events/instructions): fuente de verdad histórica hasta
    # que se dropeen en una migración de limpieza posterior. El repo sigue
    # escribiéndolas por compatibilidad/rollback, pero lee de `items` si existe.
    assignments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    instructions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)