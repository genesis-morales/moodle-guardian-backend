from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.moodle_site import MoodleSite, get_site


@dataclass
class MoodleConnection:
    """Una cuenta Moodle de un usuario en un sitio concreto (aprende/educa/…).

    Es lo que hoy vive disperso en `User` (moodle_token, moodle_user_id) pero por
    conexión: un usuario con 2 campus tiene 2 `MoodleConnection`, cada una con su token,
    su `moodle_user_id` (distinto por sitio) y su `site_key` (que deriva la `base_url`).

    El token-recovery (contador de fallos, relink, desactivación) es **por conexión**:
    el token de aprende puede morir mientras el de educa sigue vivo. La identidad estable
    de una conexión es `(site_key, moodle_user_id)`.
    """

    id: Optional[int]
    account_id: int              # FK → users.id (la cuenta/persona)
    site_key: str                # ref al catálogo MOODLE_SITES
    moodle_user_id: int          # userid DENTRO de ese sitio
    moodle_token: str
    is_active: bool = True
    token_failure_count: int = 0
    last_scan_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def site(self) -> MoodleSite:
        return get_site(self.site_key)

    @property
    def base_url(self) -> str:
        """URL del web service del sitio de esta conexión (reemplaza la global)."""
        return self.site.base_url

    def relink(self, new_token: str) -> None:
        """Re-vincula un token nuevo y reactiva la conexión (tras un token muerto)."""
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
