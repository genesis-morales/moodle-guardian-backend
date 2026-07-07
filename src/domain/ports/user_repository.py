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

    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    async def get_by_telegram_chat_id(self, telegram_chat_id: str) -> Optional[User]:
        ...

    async def list_active(self) -> List[User]:
        ...

    async def update_token_failure_count(
        self, moodle_user_id: int, count: int
    ) -> None:
        """Actualiza SOLO `token_failure_count` (sin re-cifrar el token ni pisar
        otras columnas). Lo usa el scan en cada corrida para llevar el contador
        de fallos consecutivos."""
        ...