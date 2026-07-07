from sqlalchemy import select, update

from src.domain.entities.moodle_connection import MoodleConnection
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.moodle_connection_model import MoodleConnectionModel
from src.infrastructure.security.token_cipher import TokenCipher, get_token_cipher


class PostgresMoodleConnectionRepository:
    def __init__(self, cipher: TokenCipher | None = None) -> None:
        # El cifrado del moodle_token vive acá, en la frontera con la DB: el dominio
        # siempre maneja el token en claro (igual que PostgresUserRepository).
        self._cipher = cipher or get_token_cipher()

    async def save(self, connection: MoodleConnection) -> MoodleConnection:
        async with AsyncSessionLocal() as session:
            model = MoodleConnectionModel(
                account_id=connection.account_id,
                site_key=connection.site_key,
                moodle_user_id=connection.moodle_user_id,
                moodle_token=self._cipher.encrypt(connection.moodle_token),
                is_active=connection.is_active,
                token_failure_count=connection.token_failure_count,
                last_scan_at=connection.last_scan_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def update(self, connection: MoodleConnection) -> MoodleConnection:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MoodleConnectionModel).where(
                    MoodleConnectionModel.id == connection.id
                )
            )
            model = result.scalar_one()

            model.account_id = connection.account_id
            model.site_key = connection.site_key
            model.moodle_user_id = connection.moodle_user_id
            model.moodle_token = self._cipher.encrypt(connection.moodle_token)
            model.is_active = connection.is_active
            model.token_failure_count = connection.token_failure_count
            model.last_scan_at = connection.last_scan_at

            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_by_id(self, connection_id: int) -> MoodleConnection | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MoodleConnectionModel).where(
                    MoodleConnectionModel.id == connection_id
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_site_and_moodle_user_id(
        self, site_key: str, moodle_user_id: int
    ) -> MoodleConnection | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MoodleConnectionModel).where(
                    MoodleConnectionModel.site_key == site_key,
                    MoodleConnectionModel.moodle_user_id == moodle_user_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def list_active(self) -> list[MoodleConnection]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MoodleConnectionModel).where(
                    MoodleConnectionModel.is_active.is_(True)
                )
            )
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]

    async def list_by_account_id(self, account_id: int) -> list[MoodleConnection]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MoodleConnectionModel).where(
                    MoodleConnectionModel.account_id == account_id
                )
            )
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]

    async def update_token_failure_count(
        self, connection_id: int, count: int
    ) -> None:
        # UPDATE dirigido a una sola columna: evita re-cifrar el token y pisar
        # last_scan_at en cada corrida sana.
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(MoodleConnectionModel)
                .where(MoodleConnectionModel.id == connection_id)
                .values(token_failure_count=count)
            )
            await session.commit()

    def _to_entity(self, model: MoodleConnectionModel) -> MoodleConnection:
        return MoodleConnection(
            id=model.id,
            account_id=model.account_id,
            site_key=model.site_key,
            moodle_user_id=model.moodle_user_id,
            moodle_token=self._cipher.decrypt(model.moodle_token),
            is_active=model.is_active,
            token_failure_count=model.token_failure_count,
            last_scan_at=model.last_scan_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
