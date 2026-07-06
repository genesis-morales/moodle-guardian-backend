from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Legacy: ya NO es único global (el mismo userid puede repetirse entre campus/
    # personas). La identidad de conexión vive en moodle_connections(site_key, moodle_user_id).
    moodle_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    moodle_token: Mapped[str] = mapped_column(String, nullable=False)
    # Identidad de cuenta (channel-independent). Nullable por las filas legacy; el
    # registro nuevo lo exige. Único: una cuenta por email.
    email: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )