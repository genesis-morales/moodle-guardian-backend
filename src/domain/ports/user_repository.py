from typing import Protocol, Optional, List

from src.domain.entities.user import User


class UserRepository(Protocol):
    async def save(self, user: User) -> User:
        ...

    async def update(self, user: User) -> User:
        ...

    async def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    async def get_by_moodle_user_id(self, moodle_user_id: int) -> Optional[User]:
        ...

    async def list_active(self) -> List[User]:
        ...