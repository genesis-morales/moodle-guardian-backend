import pytest
from unittest.mock import AsyncMock, Mock

from src.application.dto.guardian_dto import RelinkGuardianInput
from src.application.use_cases.relink_guardian import RelinkGuardianUseCase
from src.domain.entities.moodle_connection import MoodleConnection
from src.domain.entities.user import User
from src.domain.exceptions.registration_errors import (
    RegistrationError,
    RelinkUserNotFoundError,
)

pytestmark = pytest.mark.anyio


def _gateway_factory(valid: bool):
    gateway = Mock()
    gateway.validate_token = AsyncMock(return_value=valid)
    return lambda _base_url: gateway


def _use_case(conn_repo, *, valid_token=True, user_repo=None, dispatcher=None):
    if user_repo is None:
        user_repo = Mock()
        user_repo.get_by_id = AsyncMock(return_value=None)
    if dispatcher is None:
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock(return_value=True)
    return RelinkGuardianUseCase(
        user_repository=user_repo,
        connection_repository=conn_repo,
        moodle_gateway_factory=_gateway_factory(valid_token),
        dispatcher=dispatcher,
    )


async def test_relink_updates_connection_token_and_reactivates():
    connection = MoodleConnection(
        id=7, account_id=1, site_key="aprende", moodle_user_id=42,
        moodle_token="viejo", is_active=False,
    )
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=connection)
    conn_repo.update = AsyncMock(side_effect=lambda c: c)

    user_repo = Mock()
    user_repo.get_by_id = AsyncMock(
        return_value=User(id=1, moodle_user_id=42, moodle_token="x", telegram_chat_id="chat")
    )

    result = await _use_case(conn_repo, user_repo=user_repo).execute(
        RelinkGuardianInput(site_key="aprende", moodle_user_id=42, moodle_token="nuevo")
    )

    assert connection.moodle_token == "nuevo"
    assert connection.is_active is True
    conn_repo.update.assert_awaited_once_with(connection)
    assert result.is_active is True
    assert result.moodle_user_id == 42
    assert result.site_key == "aprende"


async def test_relink_unknown_connection_raises_not_found():
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.update = AsyncMock()

    with pytest.raises(RelinkUserNotFoundError):
        await _use_case(conn_repo).execute(
            RelinkGuardianInput(site_key="aprende", moodle_user_id=999, moodle_token="nuevo")
        )

    conn_repo.update.assert_not_awaited()


async def test_relink_invalid_token_touches_nothing():
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock()
    conn_repo.update = AsyncMock()

    with pytest.raises(RegistrationError):
        await _use_case(conn_repo, valid_token=False).execute(
            RelinkGuardianInput(site_key="aprende", moodle_user_id=42, moodle_token="malo")
        )

    conn_repo.get_by_site_and_moodle_user_id.assert_not_awaited()
    conn_repo.update.assert_not_awaited()
