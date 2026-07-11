from sqlalchemy import select

from src.domain.entities.channel_preference import ChannelPreference
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.channel_preference_model import (
    ChannelPreferenceModel,
)


class PostgresChannelPreferenceRepository:
    """Preferencias de canal por cuenta. A diferencia del repo de conexiones, el
    `address` (chat_id / correo) NO se cifra: no es un secreto de alto valor como el
    `moodle_token` (que da acceso a la cuenta Moodle)."""

    async def save(self, preference: ChannelPreference) -> ChannelPreference:
        async with AsyncSessionLocal() as session:
            model = ChannelPreferenceModel(
                account_id=preference.account_id,
                channel=preference.channel,
                address=preference.address,
                is_enabled=preference.is_enabled,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get(
        self, account_id: int, channel: str
    ) -> ChannelPreference | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChannelPreferenceModel).where(
                    ChannelPreferenceModel.account_id == account_id,
                    ChannelPreferenceModel.channel == channel,
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_by_account_id(self, account_id: int) -> list[ChannelPreference]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChannelPreferenceModel).where(
                    ChannelPreferenceModel.account_id == account_id
                )
            )
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]

    async def upsert(
        self, account_id: int, channel: str, address: str, is_enabled: bool = True
    ) -> ChannelPreference:
        # Idempotente por `(account_id, channel)`: el registro puede reintentarse sin
        # duplicar filas (hay UNIQUE en la tabla que además lo garantiza).
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ChannelPreferenceModel).where(
                    ChannelPreferenceModel.account_id == account_id,
                    ChannelPreferenceModel.channel == channel,
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                model = ChannelPreferenceModel(
                    account_id=account_id,
                    channel=channel,
                    address=address,
                    is_enabled=is_enabled,
                )
                session.add(model)
            else:
                model.address = address
                model.is_enabled = is_enabled

            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    def _to_entity(self, model: ChannelPreferenceModel) -> ChannelPreference:
        return ChannelPreference(
            id=model.id,
            account_id=model.account_id,
            channel=model.channel,
            address=model.address,
            is_enabled=model.is_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
