from typing import Optional

from src.domain.entities.snapshot import Snapshot
from src.domain.ports.snapshot_repository import SnapshotRepository


class PostgresSnapshotRepository(SnapshotRepository):
    async def save(self, snapshot: Snapshot) -> Snapshot:
        # guardar en postgres
        return snapshot

    async def get_latest_by_user_id(self, user_id: int) -> Optional[Snapshot]:
        # buscar el snapshot más reciente del usuario
        return None