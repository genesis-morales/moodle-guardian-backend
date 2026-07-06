from typing import List, Optional, Protocol

from src.domain.entities.moodle_connection import MoodleConnection


class MoodleConnectionRepository(Protocol):
    async def save(self, connection: MoodleConnection) -> MoodleConnection:
        ...

    async def update(self, connection: MoodleConnection) -> MoodleConnection:
        ...

    async def get_by_id(self, connection_id: int) -> Optional[MoodleConnection]:
        ...

    async def get_by_site_and_moodle_user_id(
        self, site_key: str, moodle_user_id: int
    ) -> Optional[MoodleConnection]:
        """Identidad estable de una conexión: `(site_key, moodle_user_id)`.

        Un mismo `moodle_user_id` puede existir en sitios distintos (aprende/educa),
        así que la búsqueda es por el par, no por el userid solo."""
        ...

    async def list_active(self) -> List[MoodleConnection]:
        ...

    async def list_by_account_id(self, account_id: int) -> List[MoodleConnection]:
        ...

    async def update_token_failure_count(self, connection_id: int, count: int) -> None:
        """Actualiza SOLO `token_failure_count` (sin re-cifrar el token ni pisar
        otras columnas). Token-recovery por conexión."""
        ...
