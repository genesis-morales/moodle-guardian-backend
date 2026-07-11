"""Fake de canal para los perfiles local/dev y para tests.

No hace red: loguea y guarda en `self.sent` lo entregado. Sirve para CUALQUIER canal
(se parametriza con `channel_key`), así el fan-out en dev muestra por consola a qué
canales habría ido cada notificación sin spamear a nadie.
"""

import logging

from src.domain.ports.channel_notifier import ChannelNotifier

logger = logging.getLogger(__name__)


class FakeChannelNotifier(ChannelNotifier):
    def __init__(self, channel_key: str) -> None:
        self.channel_key = channel_key
        # (address, subject, body) de cada entrega, para asserts en tests.
        self.sent: list[tuple[str, str | None, str]] = []

    async def deliver(self, address: str, subject: str | None, body: str) -> None:
        self.sent.append((address, subject, body))
        logger.info(
            "[FakeChannelNotifier:%s] -> %s | subject=%s\n%s",
            self.channel_key, address, subject, body,
        )
