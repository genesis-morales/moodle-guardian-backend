import httpx

from src.config.settings import get_settings
from src.domain.entities.subscription_plan import CHANNEL_TELEGRAM
from src.domain.ports.channel_notifier import ChannelNotifier


class TelegramChannelNotifier(ChannelNotifier):
    """Entrega por Telegram (Bot API sendMessage). `address` = chat_id, `body` = HTML
    del subset de Telegram, `subject` se ignora (Telegram no tiene asunto)."""

    channel_key = CHANNEL_TELEGRAM

    def __init__(self) -> None:
        self.settings = get_settings()

    async def deliver(self, address: str, subject: str | None, body: str) -> None:
        if not self.settings.telegram_bot_token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN")

        url = (
            f"{self.settings.telegram_api_base_url}/bot"
            f"{self.settings.telegram_bot_token}/sendMessage"
        )
        payload = {
            "chat_id": address,
            "text": body,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
