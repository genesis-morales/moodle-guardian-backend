import pytest
from unittest.mock import AsyncMock, Mock

import src.workers.jobs.scan_all_users as job_module
from src.workers.jobs.scan_all_users import scan_all_users_job
from src.domain.entities.user import User
from src.domain.exceptions.domain_errors import (
    MoodleTokenError,
    TokenDecryptionError,
)

pytestmark = pytest.mark.anyio


def _build_user(
    user_id: int, moodle_user_id: int, token_failure_count: int = 0
) -> User:
    return User(
        id=user_id,
        moodle_user_id=moodle_user_id,
        moodle_token="token-x",
        telegram_chat_id="chat-x",
        token_failure_count=token_failure_count,
    )


def _build_repo(user) -> Mock:
    user_repo = Mock()
    user_repo.list_active = AsyncMock(return_value=[user])
    user_repo.update = AsyncMock()
    user_repo.update_token_failure_count = AsyncMock()
    return user_repo


def _wire(
    monkeypatch,
    user_repo,
    scan_uc,
    scan_run_repo,
    notifier=None,
    message_builder=None,
    threshold=3,
) -> None:
    monkeypatch.setattr(job_module, "get_user_repository", lambda: user_repo)
    monkeypatch.setattr(
        job_module, "get_run_guardian_scan_use_case", lambda: scan_uc
    )
    monkeypatch.setattr(job_module, "get_scan_run_repository", lambda: scan_run_repo)

    if notifier is None:
        notifier = Mock()
        notifier.send_message = AsyncMock()
    if message_builder is None:
        message_builder = Mock()
        message_builder.build_token_expired_message = Mock(return_value="expired-msg")
    monkeypatch.setattr(job_module, "get_telegram_notifier", lambda: notifier)
    monkeypatch.setattr(
        job_module, "get_telegram_message_builder", lambda: message_builder
    )

    settings_stub = Mock()
    settings_stub.web_relink_url = ""
    settings_stub.token_failure_threshold = threshold
    monkeypatch.setattr(job_module, "get_settings", lambda: settings_stub)


async def test_transient_token_failure_below_threshold_does_not_deactivate(monkeypatch):
    # Un solo fallo de token con umbral 3 NO desactiva: puede ser un bache
    # transitorio de Moodle. Solo se incrementa el contador.
    user = _build_user(3, 4327)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("Ficha inválida"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo, threshold=3)

    await scan_all_users_job()

    # Sigue activo; NO se desactiva ni se llama a update(user).
    assert user.is_active is True
    user_repo.update.assert_not_awaited()
    # Se persiste el contador incrementado (1/3), con UPDATE dirigido.
    user_repo.update_token_failure_count.assert_awaited_once_with(4327, 1)

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
    assert "sin desactivar" in saved_run.failures[0].error


async def test_reaching_threshold_deactivates_and_records_failure(monkeypatch):
    # Con umbral 1, el primer fallo ya alcanza el umbral -> desactiva.
    user = _build_user(3, 4327)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("Ficha inválida"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo, threshold=1)

    await scan_all_users_job()

    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 0
    assert saved_run.failure_count == 1
    assert saved_run.failures[0].moodle_user_id == 4327
    assert "desactivado" in saved_run.failures[0].error


async def test_reaching_threshold_notifies_before_deactivating(monkeypatch):
    user = _build_user(7, 8888)  # tiene telegram_chat_id="chat-x"
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("token muerto"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    notifier = Mock()
    notifier.send_message = AsyncMock()
    builder = Mock()
    builder.build_token_expired_message = Mock(return_value="expired-msg")

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo, notifier, builder, threshold=1)

    await scan_all_users_job()

    notifier.send_message.assert_awaited_once_with(user, "expired-msg")
    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)


async def test_notify_failure_still_deactivates(monkeypatch):
    user = _build_user(8, 9999)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("token muerto"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    notifier = Mock()
    notifier.send_message = AsyncMock(side_effect=RuntimeError("telegram caído"))
    builder = Mock()
    builder.build_token_expired_message = Mock(return_value="expired-msg")

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo, notifier, builder, threshold=1)

    await scan_all_users_job()

    # El fallo de envío se traga: el usuario igual se desactiva.
    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)


async def test_at_threshold_without_chat_id_does_not_notify(monkeypatch):
    user = User(id=9, moodle_user_id=1234, moodle_token="t", telegram_chat_id=None)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=MoodleTokenError("token muerto"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    notifier = Mock()
    notifier.send_message = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo, notifier, threshold=1)

    await scan_all_users_job()

    notifier.send_message.assert_not_awaited()
    assert user.is_active is False
    user_repo.update.assert_awaited_once_with(user)


async def test_successful_scan_keeps_user_active(monkeypatch):
    user = _build_user(1, 3095)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(return_value=None)

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update.assert_not_awaited()
    # Sin fallos previos (count=0), no hay nada que resetear.
    user_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.success_count == 1
    assert saved_run.failure_count == 0


async def test_successful_scan_resets_previous_failure_count(monkeypatch):
    # Usuario que venía acumulando fallos: un scan sano limpia el contador.
    user = _build_user(1, 3095, token_failure_count=2)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(return_value=None)

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update_token_failure_count.assert_awaited_once_with(3095, 0)


async def test_generic_failure_does_not_deactivate_user(monkeypatch):
    # Un fallo transitorio (no token) NO desactiva ni toca el contador de token.
    user = _build_user(2, 5000)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=RuntimeError("moodle timeout"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update.assert_not_awaited()
    user_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
    assert saved_run.success_count == 0


async def test_token_decryption_error_does_not_deactivate_user(monkeypatch):
    # Un fallo de descifrado (clave nuestra mal) NO es culpa del token del
    # usuario: cae en el handler genérico (Sentry) y NO desactiva.
    user = _build_user(2, 5000)
    user_repo = _build_repo(user)

    scan_uc = Mock()
    scan_uc.execute = AsyncMock(side_effect=TokenDecryptionError("clave equivocada"))

    scan_run_repo = Mock()
    scan_run_repo.save = AsyncMock()

    _wire(monkeypatch, user_repo, scan_uc, scan_run_repo)

    await scan_all_users_job()

    assert user.is_active is True
    user_repo.update.assert_not_awaited()
    user_repo.update_token_failure_count.assert_not_awaited()

    saved_run = scan_run_repo.save.call_args.args[0]
    assert saved_run.failure_count == 1
