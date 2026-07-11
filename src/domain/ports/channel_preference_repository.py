from typing import List, Optional, Protocol

from src.domain.entities.channel_preference import ChannelPreference


class ChannelPreferenceRepository(Protocol):
    async def save(self, preference: ChannelPreference) -> ChannelPreference:
        ...

    async def get(
        self, account_id: int, channel: str
    ) -> Optional[ChannelPreference]:
        """Identidad estable de una preferencia: `(account_id, channel)`."""
        ...

    async def list_by_account_id(self, account_id: int) -> List[ChannelPreference]:
        ...

    async def upsert(
        self, account_id: int, channel: str, address: str, is_enabled: bool = True
    ) -> ChannelPreference:
        """Crea la preferencia `(account_id, channel)` o actualiza su dirección /
        estado si ya existe. Idempotente: el registro puede reintentarse sin duplicar."""
        ...
