import pytest
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.notify_user_changes import NotifyUserChangesUseCase
from src.domain.entities.diff_result import DiffResult
from src.domain.entities.user import User


def build_user() -> User:
    return User(id=1, moodle_user_id=3095, moodle_token="token-123")


def build_diff(has_changes: bool = True) -> DiffResult:
    if has_changes:
        return DiffResult(new_assignments=["a"])
    return DiffResult()


def build_use_case(dispatch_result: bool = True):
    dispatcher = Mock()
    dispatcher.dispatch = AsyncMock(return_value=dispatch_result)
    return NotifyUserChangesUseCase(dispatcher=dispatcher), dispatcher


@pytest.mark.anyio
async def test_execute_returns_false_when_no_changes():
    use_case, dispatcher = build_use_case()

    result = await use_case.execute(user=build_user(), diff=build_diff(has_changes=False))

    assert result is False
    dispatcher.dispatch.assert_not_awaited()


@pytest.mark.anyio
async def test_execute_returns_false_when_no_deliverable_channel():
    # El dispatcher devuelve False si la cuenta no tiene canales entregables.
    use_case, dispatcher = build_use_case(dispatch_result=False)

    result = await use_case.execute(user=build_user(), diff=build_diff(has_changes=True))

    assert result is False
    dispatcher.dispatch.assert_awaited_once()


@pytest.mark.anyio
async def test_execute_dispatches_when_there_are_changes():
    use_case, dispatcher = build_use_case(dispatch_result=True)
    user = build_user()
    diff = build_diff(has_changes=True)

    result = await use_case.execute(user=user, diff=diff, site_label="Aprende")

    assert result is True
    # El dispatcher recibe el user, una función de render y el asunto.
    args, kwargs = dispatcher.dispatch.await_args
    assert args[0] is user
    assert callable(args[1])
    assert "subject" in kwargs
