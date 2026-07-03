import pytest
from unittest.mock import AsyncMock, Mock

from src.application.dto.guardian_dto import RelinkGuardianInput
from src.application.use_cases.relink_guardian import RelinkGuardianUseCase
from src.domain.entities.user import User
from src.domain.exceptions.registration_errors import (
    RegistrationError,
    RelinkUserNotFoundError,
)

pytestmark = pytest.mark.anyio


def _use_case(user_repo, moodle_gateway, notifier=None, builder=None):
    if notifier is None:
        notifier = Mock()
        notifier.send_message = AsyncMock()
    if builder is None:
        builder = Mock()
        builder.build_relink_success_message = Mock(return_value="ok-msg")
    return RelinkGuardianUseCase(
        user_repository=user_repo,
        moodle_gateway=moodle_gateway,
        notifier=notifier,
        message_builder=builder,
    )


async def test_relink_updates_token_and_reactivates():
    user = User(id=1, moodle_user_id=42, moodle_token="viejo", telegram_chat_id="chat", is_active=False)

    user_repo = Mock()
    user_repo.get_by_moodle_user_id = AsyncMock(return_value=user)
    user_repo.update = AsyncMock(side_effect=lambda u: u)

    moodle = Mock()
    moodle.validate_token = AsyncMock(return_value=True)

    result = await _use_case(user_repo, moodle).execute(
        RelinkGuardianInput(moodle_user_id=42, moodle_token="nuevo")
    )

    assert user.moodle_token == "nuevo"
    assert user.is_active is True
    user_repo.update.assert_awaited_once_with(user)
    assert result.is_active is True
    assert result.moodle_user_id == 42


async def test_relink_unknown_user_raises_not_found():
    user_repo = Mock()
    user_repo.get_by_moodle_user_id = AsyncMock(return_value=None)
    user_repo.update = AsyncMock()

    moodle = Mock()
    moodle.validate_token = AsyncMock(return_value=True)

    with pytest.raises(RelinkUserNotFoundError):
        await _use_case(user_repo, moodle).execute(
            RelinkGuardianInput(moodle_user_id=999, moodle_token="nuevo")
        )

    user_repo.update.assert_not_awaited()


async def test_relink_invalid_token_raises_and_touches_nothing():
    user_repo = Mock()
    user_repo.get_by_moodle_user_id = AsyncMock()
    user_repo.update = AsyncMock()

    moodle = Mock()
    moodle.validate_token = AsyncMock(return_value=False)

    with pytest.raises(RegistrationError):
        await _use_case(user_repo, moodle).execute(
            RelinkGuardianInput(moodle_user_id=42, moodle_token="malo")
        )

    # Token inválido: ni siquiera busca el usuario ni actualiza.
    user_repo.get_by_moodle_user_id.assert_not_awaited()
    user_repo.update.assert_not_awaited()
