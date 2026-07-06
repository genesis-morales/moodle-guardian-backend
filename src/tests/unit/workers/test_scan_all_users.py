import pytest
from unittest.mock import AsyncMock, Mock

import src.workers.jobs.scan_all_users as job_module
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.domain.entities.moodle_connection import MoodleConnection
from src.domain.entities.user import User
from src.domain.exceptions.domain_errors import (
    MoodleTokenError,
    TokenDecryptionError,
)

pytestmark = pytest.mark.anyio


def _build_connection(
    conn_id: int, moodle_user_id: int, *, site_key: str = "aprende",
    token_failure_count: int = 0, account_id: int = 100,
) -> MoodleConnection:
    return MoodleConnection(
        id=conn_id,
        account_id=account_id,
        site_key=site_key,
        moodle_user_id=moodle_user_id,
        moodle_token="token-x",
        token_failure_count=token_failure_count,
    )


def _account(chat_id: str | None = "chat-x") -> User:
    return User(id=100, moodle_user_id=1, moodle_token="t",
                email="a@b.com", telegram_chat_id=chat_id)


def _build_repos(connection, account=None):
    conn_repo = Mock()
    conn_repo.list_active = AsyncMock(return_value=[connection])
    conn_repo.update = AsyncMock()
    conn_repo.update_token_failure_count = AsyncMock()

    user_repo = Mock()
    user_repo.get_by_id = AsyncMock(return_value=account if account is not None else _account())
    return conn_repo, user_repo


def _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo,
          notifier=None, message_builder=None, threshold=3) -> None:
    monkeypatch.setattr(job_module, "get_moodle_connection_repository", lambda: conn_repo)
    monkeypatch.setattr(job_module, "get_user_repository", lambda: user_repo)
    monkeypatch.setattr(job_module, "get_run_guardian_scan_use_case", lambda: scan_uc)
    monkeypatch.setattr(job_module, "get_scan_run_repository", lambda: scan_run_repo)

    if notifier is None:
        notifier = Mock()
        notifier.send_message = AsyncMock()
    if message_builder is None:
        message_builder = Mock()
        message_builder.build_token_expired_message = Mock(return_value="expired-msg")
    monkeypatch.setattr(job_module, "get_telegram_notifier", lambda: notifier)
    monkeypatch.setattr(job_module, "get_telegram_message_builder", lambda: message_builder)

    settings_stub = Mock()
    settings_stub.web_relink_url = ""
    settings_stub.token_failure_threshold = threshold
    monkeypatch.setattr(job_module, "get_settings", lambda: settings_stub)


def _scan_uc(side_effect=None, return_value=None) -> Mock:
    uc = Mock()
    uc.execute_for_connection = AsyncMock(side_effect=side_effect, return_value=return_value)
    return uc


async def test_transient_token_failure_below_threshold_does_not_deactivate(monkeypatch):
    conn = _build_connection(3, 4327)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(side_effect=MoodleTokenError("Ficha inválida"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo, threshold=3)
    await scan_all_users_job()

    assert conn.is_active is True
    conn_repo.update.assert_not_awaited()
    conn_repo.update_token_failure_count.assert_awaited_once_with(3, 1)

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
    assert "sin desactivar" in saved_run.failures[0].error


async def test_reaching_threshold_deactivates_and_records_failure(monkeypatch):
    conn = _build_connection(3, 4327)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(side_effect=MoodleTokenError("Ficha inválida"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo, threshold=1)
    await scan_all_users_job()

    assert conn.is_active is False
    conn_repo.update.assert_awaited_once_with(conn)

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 0
    assert saved_run.failure_count == 1
    assert saved_run.failures[0].moodle_user_id == 4327
    assert "desactivada" in saved_run.failures[0].error


async def test_reaching_threshold_notifies_before_deactivating(monkeypatch):
    conn = _build_connection(7, 8888)
    account = _account(chat_id="chat-x")
    conn_repo, user_repo = _build_repos(conn, account)
    scan_uc = _scan_uc(side_effect=MoodleTokenError("token muerto"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    notifier = Mock(); notifier.send_message = AsyncMock()
    builder = Mock(); builder.build_token_expired_message = Mock(return_value="expired-msg")

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo, notifier, builder, threshold=1)
    await scan_all_users_job()

    notifier.send_message.assert_awaited_once_with(account, "expired-msg")
    # El aviso incluye la etiqueta del campus.
    builder.build_token_expired_message.assert_called_once_with("", site_label="Aprende")
    assert conn.is_active is False
    conn_repo.update.assert_awaited_once_with(conn)


async def test_notify_failure_still_deactivates(monkeypatch):
    conn = _build_connection(8, 9999)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(side_effect=MoodleTokenError("token muerto"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    notifier = Mock(); notifier.send_message = AsyncMock(side_effect=RuntimeError("telegram caído"))
    builder = Mock(); builder.build_token_expired_message = Mock(return_value="expired-msg")

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo, notifier, builder, threshold=1)
    await scan_all_users_job()

    assert conn.is_active is False
    conn_repo.update.assert_awaited_once_with(conn)


async def test_at_threshold_without_chat_id_does_not_notify(monkeypatch):
    conn = _build_connection(9, 1234)
    account = _account(chat_id=None)
    conn_repo, user_repo = _build_repos(conn, account)
    scan_uc = _scan_uc(side_effect=MoodleTokenError("token muerto"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    notifier = Mock(); notifier.send_message = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo, notifier, threshold=1)
    await scan_all_users_job()

    notifier.send_message.assert_not_awaited()
    assert conn.is_active is False
    conn_repo.update.assert_awaited_once_with(conn)


async def test_successful_scan_keeps_connection_active(monkeypatch):
    conn = _build_connection(1, 3095)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(return_value=None)
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo)
    await scan_all_users_job()

    assert conn.is_active is True
    conn_repo.update.assert_not_awaited()
    conn_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 1
    assert saved_run.failure_count == 0


async def test_successful_scan_resets_previous_failure_count(monkeypatch):
    conn = _build_connection(1, 3095, token_failure_count=2)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(return_value=None)
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo)
    await scan_all_users_job()

    assert conn.is_active is True
    conn_repo.update_token_failure_count.assert_awaited_once_with(1, 0)


async def test_generic_failure_does_not_deactivate_connection(monkeypatch):
    conn = _build_connection(2, 5000)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(side_effect=RuntimeError("moodle timeout"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo)
    await scan_all_users_job()

    assert conn.is_active is True
    conn_repo.update.assert_not_awaited()
    conn_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
    assert saved_run.success_count == 0


async def test_token_decryption_error_does_not_deactivate_connection(monkeypatch):
    conn = _build_connection(2, 5000)
    conn_repo, user_repo = _build_repos(conn)
    scan_uc = _scan_uc(side_effect=TokenDecryptionError("clave equivocada"))
    scan_run_repo = Mock(); scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, conn_repo, user_repo, scan_uc, scan_run_repo)
    await scan_all_users_job()

    assert conn.is_active is True
    conn_repo.update.assert_not_awaited()
    conn_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
