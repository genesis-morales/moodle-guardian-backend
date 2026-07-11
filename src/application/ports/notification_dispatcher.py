from typing import Callable, Protocol

from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.user import User

# Una función que, dado el builder de UN canal, devuelve el cuerpo renderizado para
# ese canal. El caso de uso decide QUÉ mensaje (changes/digest/welcome…); el
# dispatcher decide POR QUÉ canales y con qué builder. Así se agregan tipos de
# notificación sin tocar el dispatcher, y canales sin tocar los casos de uso.
Render = Callable[[NotificationMessageBuilder], str]


class NotificationDispatcher(Protocol):
    async def dispatch(self, user: User, render: Render, subject: str) -> bool:
        """Entrega la notificación por TODOS los canales activos de la cuenta que el
        plan permita (fan-out). Devuelve True si al menos un canal entregó; False si la
        cuenta no tiene canales entregables. Si hay canales pero TODOS fallan, levanta
        excepción (para que el scan no guarde snapshot y reintente)."""
        ...
