from typing import Protocol

from src.application.dto.digest_dto import DeliverableItem
from src.domain.entities.diff_result import DiffResult


class NotificationMessageBuilder(Protocol):
    def build_welcome_message(self) -> str:
        ...

    def build_test_message(self) -> str:
        ...

    def build_changes_message(self, diff: DiffResult) -> str:
        ...

    def build_weekly_digest_message(self, items: list[DeliverableItem]) -> str:
        ...

    def build_deadline_reminder_message(
        self, items: list[DeliverableItem], days: int
    ) -> str:
        ...

    def build_token_expired_message(self, relink_url: str) -> str:
        ...

    def build_relink_success_message(self) -> str:
        ...