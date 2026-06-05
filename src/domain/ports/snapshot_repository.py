from typing import Protocol, Optional, List

from src.domain.entities.snapshot import Snapshot


class SnapshotRepository(Protocol):
    async def save(self, snapshot: Snapshot) -> Snapshot:
        ...

    async def get_latest(self, user_id: int, course_id: int) -> Optional[Snapshot]:
        ...

    async def list_by_user(self, user_id: int) -> List[Snapshot]:
        ...

    async def delete_older_than_days(self, days: int) -> int:
        ...