from typing import Protocol

from src.domain.entities.scan_run import ScanRun


class ScanRunRepository(Protocol):
    async def save(self, run: ScanRun) -> ScanRun:
        ...

    async def list_recent(self, limit: int = 20) -> list[ScanRun]:
        ...
