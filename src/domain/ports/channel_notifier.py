from typing import Protocol


class ChannelNotifier(Protocol):
    """Entrega de bajo nivel por UN canal concreto (Telegram, email, …).

    A diferencia del viejo `NotifierGateway` (tipado sobre `User` + mensaje ya
    armado), este puerto es agnóstico de cuenta: recibe la dirección de entrega y el
    cuerpo YA renderizado para su canal. El dispatcher resuelve la dirección desde las
    preferencias de la cuenta y arma el cuerpo con el builder del canal.

    `channel_key` identifica el canal (usa las constantes de subscription_plan:
    CHANNEL_TELEGRAM, CHANNEL_EMAIL, …) para emparejarlo con su builder y su
    preferencia.
    """

    channel_key: str

    async def deliver(self, address: str, subject: str | None, body: str) -> None:
        """Entrega `body` a `address`. `subject` solo lo usan canales que lo tienen
        (email); los que no (Telegram) lo ignoran."""
        ...
