from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.database import Base


class MoodleConnectionModel(Base):
    __tablename__ = "moodle_connections"
    __table_args__ = (
        # Identidad estable de una conexión. Un mismo moodle_user_id puede repetirse
        # entre sitios (aprende/educa), pero no dentro del mismo sitio.
        UniqueConstraint("site_key", "moodle_user_id", name="uq_connection_site_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    moodle_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    moodle_token: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True, index=True
    )
    token_failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    last_scan_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
