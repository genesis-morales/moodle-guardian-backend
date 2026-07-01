import pytest
from unittest.mock import AsyncMock, Mock

import src.workers.jobs.scan_all_users as job_module
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.domain.entities.user import User
from src.domain.exceptions.domain_errors import MoodleTokenError

pytestmark = pytest.mark.anyio


def _build_user(user_id: int, moodle_user_id: int) -> User:
    return User(
        id=user_id,
        moodle_user_id=moodle_user_id,
        moodle_token="token-x",
        telegram_chat_id="chat-x",
    )


def _wire(monkeypatch, user_repo, scan_uc, scan_run_repo) -> None:
    monkeypatch.setattr(job_module, "get_user_repository", lambda: user_repo)
    monkeypatch.setattr(
        job_module, "get_run_guardian_scan_use_case", lambda: scan_uc
    )
    monkeypatch.setattr(job_module, "get_scan_run_repository", lambda: scan_run_repo)


async def test_invalid_token_deactivates_user_and_records_failure(monkeypatch):
    user = _build_user(3, 4327)

    user_repo = Mock()
    user_repo.list_active = AsyncMock(return_value=[user])
    user_repo.update = AsyncMock()

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("Ficha inválida"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    # El usuario se desactiva y se persiste, para salir del loop en próximas corridas.
    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)

    # La corrida queda registrada con el fallo etiquetado como token.
    scan_run_repo.save.assert_awaited_once()
    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 0
    assert saved_run.failure_count == 1
    assert len(saved_run.failures) == 1
    assert saved_run.failures[0].moodle_user_id == 4327
    assert "MoodleTokenError" in saved_run.failures[0].error


async def test_successful_scan_keeps_user_active(monkeypatch):
    user = _build_user(1, 3095)

    user_repo = Mock()
    user_repo.list_active = AsyncMock(return_value=[user])
    user_repo.update = AsyncMock()

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(return_value=None)

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 1
    assert saved_run.failure_count == 0


async def test_generic_failure_does_not_deactivate_user(monkeypatch):
    # Un fallo transitorio (no token) NO debe desactivar al usuario: se reintenta.
    user = _build_user(2, 5000)

    user_repo = Mock()
    user_repo.list_active = AsyncMock(return_value=[user])
    user_repo.update = AsyncMock()

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=RuntimeError("moodle timeout"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
    assert saved_run.success_count == 0
