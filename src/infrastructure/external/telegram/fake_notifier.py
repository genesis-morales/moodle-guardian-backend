"""Fake notifier para los perfiles `local`/`dev` del factory de entornos.

No hace red: loguea el mensaje y lo guarda en `self.sent` para poder inspeccionarlo
en tests/preview. Evita spamear a usuarios reales de Telegram mientras se desarrolla.
Implementa el mismo puerto que `TelegramBotNotifier`.
"""

import logging

from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User
from src.domain.ports.notifier_gateway import NotifierGateway

logger = logging.getLogger(__name__)


class FakeNotifier(NotifierGateway):
    def __init__(self) -> None:
        # Registro de lo "enviado": (tipo, user_id, mensaje). Útil para asserts.
        self.sent: list[tuple[str, int | None, str]] = []

    async def send_message(self, user: User, message: str) -> None:
        self._record("message", user, message)

    async def send_changes(self, user: User, diff: DiffResult) -> None:
        self._record("changes", user, "<cambios detectados>")

    async def send_weekly_digest(self, user: User, message: str) -> None:
        self._record("digest", user, message)

    def _record(self, kind: str, user: User, message: str) -> None:
        self.sent.append((kind, user.id, message))
        logger.info(
            "[FakeNotifier] %s -> user=%s chat=%s\n%s",
            kind, user.id, user.telegram_chat_id, message,
        )
