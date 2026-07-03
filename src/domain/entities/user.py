from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int]
    moodle_user_id: int
    moodle_token: str
    telegram_chat_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_scan_at: Optional[datetime] = None
    # Corridas consecutivas del scan que fallaron con MoodleTokenError. Un bache
    # transitorio de Moodle no debe desactivar al usuario: solo se desactiva al
    # alcanzar `settings.token_failure_threshold`. Un scan exitoso lo resetea.
    token_failure_count: int = 0

    def link_telegram(self, chat_id: str) -> None:
        self.telegram_chat_id = chat_id

    def relink(self, new_token: str) -> None:
        """Re-vincula un token nuevo y reactiva al usuario (recuperación tras un
        token muerto). Inverso de deactivate()."""
        self.moodle_token = new_token
        self.is_active = True
        self.clear_token_failures()

    def mark_scanned(self, scanned_at: datetime) -> None:
        self.last_scan_at = scanned_at

    def register_token_failure(self) -> None:
        """Suma un fallo de token consecutivo (el scan lo compara con el umbral)."""
        self.token_failure_count += 1

    def clear_token_failures(self) -> None:
        """Resetea el contador (tras un scan exitoso o un re-vínculo)."""
        self.token_failure_count = 0

    def deactivate(self) -> None:
        self.is_active = False
        self.clear_token_failures()