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

    def link_telegram(self, chat_id: str) -> None:
        self.telegram_chat_id = chat_id

    def relink(self, new_token: str) -> None:
        """Re-vincula un token nuevo y reactiva al usuario (recuperación tras un
        token muerto). Inverso de deactivate()."""
        self.moodle_token = new_token
        self.is_active = True

    def mark_scanned(self, scanned_at: datetime) -> None:
        self.last_scan_at = scanned_at

    def deactivate(self) -> None:
        self.is_active = False