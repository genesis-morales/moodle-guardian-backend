import httpx

from src.config.settings import get_settings
from src.domain.entities.subscription_plan import CHANNEL_EMAIL
from src.domain.ports.channel_notifier import ChannelNotifier


class BrevoEmailNotifier(ChannelNotifier):
    """Entrega por email vía la API HTTP de Brevo (`POST /smtp/email`).

    `address` = correo destino, `subject` = asunto, `body` = HTML de email. El
    remitente sale de settings (correo verificado en Brevo). Sigue el patrón httpx de
    los otros adapters (no usamos el SDK de Brevo, por consistencia)."""

    channel_key = CHANNEL_EMAIL

    def __init__(self) -> None:
        self.settings = get_settings()

    async def deliver(self, address: str, subject: str | None, body: str) -> None:
        if not self.settings.brevo_api_key or not self.settings.brevo_sender_email:
            raise ValueError("Missing BREVO_API_KEY / BREVO_SENDER_EMAIL")

        url = f"{self.settings.brevo_api_base_url}/smtp/email"
        payload = {
            "sender": {
                "email": self.settings.brevo_sender_email,
                "name": self.settings.brevo_sender_name,
            },
            "to": [{"email": address}],
            "subject": subject or self.settings.brevo_sender_name,
            "htmlContent": body,
        }
        headers = {
            "api-key": self.settings.brevo_api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
