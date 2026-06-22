from datetime import datetime

from sqlalchemy import select

from src.domain.ports.sent_reminder_repository import SentReminderRepository
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.sent_reminder_model import SentReminderModel


class PostgresSentReminderRepository(SentReminderRepository):
    async def latest_deadlines(
        self, user_id: int, notification_type: str
    ) -> dict[str, datetime | None]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(
                    SentReminderModel.deliverable_key,
                    SentReminderModel.deadline_snapshot,
                )
                .where(
                    SentReminderModel.user_id == user_id,
                    SentReminderModel.notification_type == notification_type,
                    SentReminderModel.deliverable_key.is_not(None),
                )
                .order_by(SentReminderModel.sent_at.desc())
            )

            latest: dict[str, datetime | None] = {}
            for key, deadline in result.all():
                # El primero que vemos por key es el más reciente (orden desc).
                if key not in latest:
                    latest[key] = deadline
            return latest

    async def record(
        self,
        user_id: int,
        notification_type: str,
        deliverable_key: str | None,
        deadline_snapshot: datetime | None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                SentReminderModel(
                    user_id=user_id,
                    notification_type=notification_type,
                    deliverable_key=deliverable_key,
                    deadline_snapshot=deadline_snapshot,
                )
            )
            await session.commit()
