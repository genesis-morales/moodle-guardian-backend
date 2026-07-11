from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChannelPreference:
    """Un canal de notificación ACTIVADO por una cuenta, con su dirección de entrega.

    Es la preferencia por-cuenta que el catálogo de planes (`subscription_plan.py`)
    anticipa: el `plan` define el TECHO de canales permitidos; esta entidad guarda
    cuáles prendió de verdad la cuenta (un subconjunto ⊆ plan) y con qué dirección
    (chat_id para Telegram, correo para email). Es la fuente de verdad de "por dónde
    notificar", 1..N por cuenta, análoga a `MoodleConnection`.

    `channel` usa las constantes estables de `subscription_plan.py` (CHANNEL_TELEGRAM,
    CHANNEL_EMAIL, …). La identidad estable es `(account_id, channel)`: una cuenta tiene
    a lo sumo una preferencia por canal.
    """

    id: Optional[int]
    account_id: int              # FK → users.id (la cuenta/persona)
    channel: str                 # CHANNEL_TELEGRAM | CHANNEL_EMAIL | …
    address: str                 # destino: chat_id (telegram) / correo (email)
    is_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def enable(self, address: str) -> None:
        """Prende el canal (y fija/actualiza su dirección de entrega)."""
        self.address = address
        self.is_enabled = True

    def disable(self) -> None:
        self.is_enabled = False
