from typing import Optional, Protocol

from src.domain.entities.snapshot import Snapshot


class SnapshotRepository(Protocol):
    async def save(self, snapshot: Snapshot) -> Snapshot:
        ...

    async def get_latest_by_user_id(self, user_id: int) -> Optional[Snapshot]:
        ...

    async def get_latest_by_connection_id(
        self, connection_id: int
    ) -> Optional[Snapshot]:
        ...