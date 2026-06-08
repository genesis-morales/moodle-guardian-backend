import pytest
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.notify_user_changes import NotifyUserChangesUseCase
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User


def build_user(telegram_chat_id: str | None = "chat-123") -> User:
    return User(
        id=1,
        moodle_user_id=3095,
        moodle_token="token-123",
        telegram_chat_id=telegram_chat_id,
    )


def build_diff(has_changes: bool = True) -> DiffResult:
    if has_changes:
        return DiffResult(
            new_assignments=["a"],
            updated_assignments=[],
            removed_assignments=[],
            new_events=[],
            updated_events=[],
            removed_events=[],
        )
    return DiffResult()


def build_use_case():
    notifier = Mock()
    notifier.send_message = AsyncMock(return_value=None)

    message_builder = Mock()
    message_builder.build_changes_message = Mock(return_value="Cambios detectados")

    use_case = NotifyUserChangesUseCase(
        notifier=notifier,
        message_builder=message_builder,
    )

    return use_case, notifier, message_builder


@pytest.mark.anyio
async def test_execute_returns_false_when_no_changes():
    use_case, notifier, message_builder = build_use_case()

    result = await use_case.execute(
        user=build_user(),
        diff=build_diff(has_changes=False),
    )

    assert result is False
    message_builder.build_changes_message.assert_not_called()
    notifier.send_message.assert_not_awaited()


@pytest.mark.anyio
async def test_execute_returns_false_when_user_has_no_telegram_chat_id():
    use_case, notifier, message_builder = build_use_case()

    result = await use_case.execute(
        user=build_user(telegram_chat_id=None),
        diff=build_diff(has_changes=True),
    )

    assert result is False
    message_builder.build_changes_message.assert_not_called()
    notifier.send_message.assert_not_awaited()


@pytest.mark.anyio
async def test_execute_sends_notification_when_there_are_changes():
    use_case, notifier, message_builder = build_use_case()
    user = build_user()
    diff = build_diff(has_changes=True)

    result = await use_case.execute(
        user=user,
        diff=diff,
    )

    assert result is True
    message_builder.build_changes_message.assert_called_once_with(diff)
    notifier.send_message.assert_awaited_once_with(user, "Cambios detectados")