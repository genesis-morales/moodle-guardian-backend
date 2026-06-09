from sqlalchemy import select

from src.domain.entities.user import User
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.user_model import UserModel

class PostgresUserRepository:
    async def save(self, user: User) -> User:
        async with AsyncSessionLocal() as session:
            model = UserModel(
                moodle_user_id=user.moodle_user_id,
                moodle_token=user.moodle_token,
                telegram_chat_id=user.telegram_chat_id,
                is_active=user.is_active,
                last_scan_at=user.last_scan_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def update(self, user: User) -> User:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user.id))
            model = result.scalar_one()

            model.moodle_user_id = user.moodle_user_id
            model.moodle_token = user.moodle_token
            model.telegram_chat_id = user.telegram_chat_id
            model.is_active = user.is_active
            model.last_scan_at = user.last_scan_at

            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_by_id(self, user_id: int) -> User | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_moodle_user_id(self, moodle_user_id: int) -> User | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.moodle_user_id == moodle_user_id)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_active(self) -> list[User]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.is_active.is_(True))
            )
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]

    async def get_by_telegram_chat_id(self, telegram_chat_id: str) -> User | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.telegram_chat_id == telegram_chat_id)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            moodle_user_id=model.moodle_user_id,
            moodle_token=model.moodle_token,
            telegram_chat_id=model.telegram_chat_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_scan_at=model.last_scan_at,
        )