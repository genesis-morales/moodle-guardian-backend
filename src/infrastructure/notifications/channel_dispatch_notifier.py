import logging

from src.application.ports.notification_dispatcher import Render
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.subscription_plan import plan_allows
from src.domain.entities.user import User
from src.domain.ports.channel_notifier import ChannelNotifier
from src.domain.ports.channel_preference_repository import (
    ChannelPreferenceRepository,
)

logger = logging.getLogger(__name__)


class ChannelDispatchNotifier:
    """Fan-out de notificaciones por los canales activos de una cuenta.

    Resuelve, para la cuenta del `user`, sus preferencias de canal habilitadas ∩ las
    que el plan permite (`plan_allows`), y por cada una arma el cuerpo con el builder
    de ESE canal y lo entrega por su `ChannelNotifier`. Un canal sin builder/notifier
    registrado se ignora (p. ej. WhatsApp antes de existir su adapter).
    """

    def __init__(
        self,
        channel_preference_repository: ChannelPreferenceRepository,
        channels: dict[str, tuple[ChannelNotifier, NotificationMessageBuilder]],
    ) -> None:
        self.channel_preference_repository = channel_preference_repository
        self.channels = channels

    async def dispatch(self, user: User, render: Render, subject: str) -> bool:
        preferences = await self.channel_preference_repository.list_by_account_id(
            user.id
        )
        targets = [
            pref
            for pref in preferences
            if pref.is_enabled
            and pref.channel in self.channels
            and plan_allows(user.plan, pref.channel)
        ]

        if not targets:
            logger.info(
                "Sin canales entregables para account_id=%s (plan=%s)",
                user.id, user.plan,
            )
            return False

        delivered = 0
        failures = 0
        for pref in targets:
            notifier, builder = self.channels[pref.channel]
            try:
                body = render(builder)
                await notifier.deliver(pref.address, subject, body)
                delivered += 1
                logger.info(
                    "Entregado por %s a account_id=%s", pref.channel, user.id
                )
            except Exception:
                failures += 1
                logger.exception(
                    "Fallo entregando por %s a account_id=%s", pref.channel, user.id
                )

        # Best-effort: si al menos un canal entregó, damos la notificación por hecha
        # (evita re-notificar por TODOS los canales si solo uno falló). Si NINGÚN canal
        # entregó habiendo destinos, propagamos el fallo: el scan no guarda snapshot y
        # reintenta en el próximo ciclo (misma invariante que el envío mono-canal).
        if delivered == 0:
            raise RuntimeError(
                f"Ningún canal entregó para account_id={user.id} ({failures} fallos)"
            )
        return True
