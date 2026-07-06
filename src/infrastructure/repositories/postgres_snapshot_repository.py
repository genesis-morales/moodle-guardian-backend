from typing import Optional

from sqlalchemy import select

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.source_registry import SOURCE_CLASSES
from src.domain.entities.source_type import SourceType
from src.domain.ports.snapshot_repository import SnapshotRepository
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.snapshot_model import SnapshotModel


class PostgresSnapshotRepository(SnapshotRepository):
    async def save(self, snapshot: Snapshot) -> Snapshot:
        if snapshot.user_id is None:
            raise ValueError("snapshot.user_id is required")

        # Almacén genérico: cada fuente serializa con su propio `to_dict()`.
        items_json = {
            source_type: [item.to_dict() for item in items]
            for source_type, items in snapshot.items.items()
        }

        async with AsyncSessionLocal() as session:
            model = SnapshotModel(
                user_id=snapshot.user_id,
                moodle_user_id=snapshot.moodle_user_id,
                captured_at=snapshot.captured_at,
                items=items_json,
                # Columnas legacy: se siguen escribiendo por seguridad de rollback
                # mientras existan. Salen del mismo `items` vía las propiedades compat.
                assignments=items_json.get(SourceType.ASSIGNMENT, []),
                events=items_json.get(SourceType.EVENT, []),
                instructions=items_json.get(SourceType.INSTRUCTION, []),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_latest_by_user_id(self, user_id: int) -> Optional[Snapshot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SnapshotModel)
                .where(SnapshotModel.user_id == user_id)
                .order_by(SnapshotModel.captured_at.desc())
            )
            model = result.scalars().first()
            return self._to_entity(model) if model else None

    def _to_entity(self, model: SnapshotModel) -> Snapshot:
        raw = model.items or {}
        if raw:
            items = {
                source_type: [SOURCE_CLASSES[source_type].from_dict(d) for d in dicts]
                for source_type, dicts in raw.items()
                if source_type in SOURCE_CLASSES  # ignora fuentes desconocidas (forward-compat)
            }
        else:
            # Fila pre-migración (sin `items`): reconstruye desde las columnas legacy.
            items = {
                SourceType.ASSIGNMENT: [Assignment.from_dict(d) for d in (model.assignments or [])],
                SourceType.EVENT: [CalendarEvent.from_dict(d) for d in (model.events or [])],
                SourceType.INSTRUCTION: [Instruction.from_dict(d) for d in (model.instructions or [])],
            }

        return Snapshot(
            user_id=model.user_id,
            moodle_user_id=model.moodle_user_id,
            captured_at=model.captured_at,
            items=items,
        )
