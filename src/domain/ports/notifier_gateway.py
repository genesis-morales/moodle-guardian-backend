from typing import Protocol

from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User


class NotifierGateway(Protocol):
    async def send_changes(self, user: User, diff: DiffResult) -> None:
        ...

    async def send_weekly_digest(self, user: User, message: str) -> None:
        ...