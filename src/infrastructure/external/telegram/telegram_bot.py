import httpx

from src.config.settings import get_settings
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User
from src.domain.ports.notifier_gateway import NotifierGateway


class TelegramBotNotifier(NotifierGateway):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_message(self, user: User, message: str) -> None:
        if not self.settings.telegram_bot_token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN")

        if not user.telegram_chat_id:
            raise ValueError("User has no telegram_chat_id linked")

        url = (
            f"{self.settings.telegram_api_base_url}/bot"
            f"{self.settings.telegram_bot_token}/sendMessage"
        )

        payload = {
            "chat_id": user.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    async def send_changes(self, user: User, diff: DiffResult) -> None:
        message = "<b>Guardian UNED</b>\n\nHay cambios nuevos en tu plataforma."
        await self.send_message(user, message)

    async def send_weekly_digest(self, user: User, message: str) -> None:
        await self.send_message(user, message)