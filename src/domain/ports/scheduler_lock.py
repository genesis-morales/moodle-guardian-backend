from typing import Protocol


class SchedulerLock(Protocol):
    async def acquire(self, key: str) -> bool:
        ...

    async def release(self, key: str) -> None:
        ...