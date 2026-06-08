from typing import Protocol

from src.domain.entities.diff_result import DiffResult


class NotificationMessageBuilder(Protocol):
    def build_welcome_message(self) -> str:
        ...

    def build_test_message(self) -> str:
        ...

    def build_changes_message(self, diff: DiffResult) -> str:
        ...