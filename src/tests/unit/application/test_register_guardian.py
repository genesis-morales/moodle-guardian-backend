import pytest
from unittest.mock import AsyncMock, Mock

from src.application.dto.guardian_dto import RegisterGuardianInput
from src.application.use_cases.register_guardian import RegisterGuardianUseCase
from src.domain.entities.moodle_connection import MoodleConnection
from src.domain.entities.user import User
from src.domain.exceptions.registration_errors import RegistrationError

pytestmark = pytest.mark.anyio


def _gateway_factory(valid: bool = True):
    gateway = Mock()
    gateway.validate_token = AsyncMock(return_value=valid)
    return lambda _base_url: gateway


def _use_case(*, user_repo, conn_repo, valid_token=True, dispatcher=None, pref_repo=None):
    if dispatcher is None:
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock(return_value=True)
    if pref_repo is None:
        pref_repo = Mock()
        pref_repo.upsert = AsyncMock()
    return RegisterGuardianUseCase(
        user_repository=user_repo,
        connection_repository=conn_repo,
        moodle_gateway_factory=_gateway_factory(valid_token),
        dispatcher=dispatcher,
        channel_preference_repository=pref_repo,
    )


def _input(**kw):
    base = dict(
        email="a@b.com", moodle_user_id=42, moodle_token="tok",
        site_key="aprende", telegram_chat_id="chat",
    )
    base.update(kw)
    return RegisterGuardianInput(**base)


async def test_new_account_creates_user_and_connection():
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_telegram_chat_id = AsyncMock(return_value=None)
    user_repo.save = AsyncMock(
        return_value=User(id=1, moodle_user_id=42, moodle_token="tok",
                          email="a@b.com", telegram_chat_id="chat", plan="escudo")
    )
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.save = AsyncMock()

    result = await _use_case(user_repo=user_repo, conn_repo=conn_repo).execute(
        _input(plan="escudo")
    )

    user_repo.save.assert_awaited_once()
    # El tier elegido se persiste en la cuenta nueva y se devuelve en el output.
    assert user_repo.save.await_args.args[0].plan == "escudo"
    assert result.plan == "escudo"
    conn_repo.save.assert_awaited_once()
    saved_conn = conn_repo.save.await_args.args[0]
    assert isinstance(saved_conn, MoodleConnection)
    assert (saved_conn.account_id, saved_conn.site_key) == (1, "aprende")
    assert result.message == "Usuario registrado correctamente."
    assert result.site_key == "aprende"


async def test_new_account_creates_channel_preferences():
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_telegram_chat_id = AsyncMock(return_value=None)
    user_repo.save = AsyncMock(
        return_value=User(id=7, moodle_user_id=42, moodle_token="tok",
                          email="a@b.com", telegram_chat_id="chat", plan="escudo")
    )
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.save = AsyncMock()
    pref_repo = Mock()
    pref_repo.upsert = AsyncMock()

    await _use_case(user_repo=user_repo, conn_repo=conn_repo, pref_repo=pref_repo).execute(
        _input(plan="escudo")
    )

    # Se crean dos preferencias: telegram (chat pegado) y email (correo de la cuenta).
    channels = {call.args[1] for call in pref_repo.upsert.await_args_list}
    assert channels == {"telegram", "email"}
    # En plan escudo el email SÍ está permitido -> habilitado.
    email_call = next(c for c in pref_repo.upsert.await_args_list if c.args[1] == "email")
    assert email_call.kwargs["is_enabled"] is True


async def test_new_account_email_pref_disabled_when_plan_forbids():
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_telegram_chat_id = AsyncMock(return_value=None)
    user_repo.save = AsyncMock(
        return_value=User(id=7, moodle_user_id=42, moodle_token="tok",
                          email="a@b.com", telegram_chat_id="chat", plan="alerta")
    )
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.save = AsyncMock()
    pref_repo = Mock()
    pref_repo.upsert = AsyncMock()

    await _use_case(user_repo=user_repo, conn_repo=conn_repo, pref_repo=pref_repo).execute(
        _input(plan="alerta")
    )

    # Plan alerta no permite email: la preferencia se crea pero apagada.
    email_call = next(c for c in pref_repo.upsert.await_args_list if c.args[1] == "email")
    assert email_call.kwargs["is_enabled"] is False


async def test_adding_campus_keeps_existing_account_plan():
    # Subir de tier es upgrade con pago (feat 3): vincular otro campus NO cambia el plan.
    existing = User(id=1, moodle_user_id=42, moodle_token="tok",
                    email="a@b.com", telegram_chat_id="chat", plan="guardian")
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock(return_value=existing)
    user_repo.save = AsyncMock()
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.save = AsyncMock()

    result = await _use_case(user_repo=user_repo, conn_repo=conn_repo).execute(
        _input(site_key="educa", moodle_user_id=99, plan="alerta")
    )

    user_repo.save.assert_not_awaited()
    assert result.plan == "guardian"  # se conserva el plan de la cuenta, no el del POST


async def test_second_campus_same_email_adds_connection_without_new_account():
    existing = User(id=1, moodle_user_id=42, moodle_token="tok",
                    email="a@b.com", telegram_chat_id="chat")
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock(return_value=existing)
    user_repo.save = AsyncMock()  # no debe llamarse
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(return_value=None)
    conn_repo.save = AsyncMock()

    result = await _use_case(user_repo=user_repo, conn_repo=conn_repo).execute(
        _input(site_key="educa", moodle_user_id=99)
    )

    user_repo.save.assert_not_awaited()  # cuenta existente: no se recrea
    conn_repo.save.assert_awaited_once()
    saved_conn = conn_repo.save.await_args.args[0]
    assert (saved_conn.account_id, saved_conn.site_key, saved_conn.moodle_user_id) == (1, "educa", 99)
    assert "educa".lower() in result.message.lower() or "Educa" in result.message


async def test_duplicate_connection_is_rejected():
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock()
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock(
        return_value=MoodleConnection(id=5, account_id=1, site_key="aprende",
                                      moodle_user_id=42, moodle_token="x")
    )
    conn_repo.save = AsyncMock()

    with pytest.raises(RegistrationError):
        await _use_case(user_repo=user_repo, conn_repo=conn_repo).execute(_input())

    conn_repo.save.assert_not_awaited()


async def test_invalid_token_rejected_before_touching_db():
    user_repo = Mock()
    user_repo.get_by_email = AsyncMock()
    conn_repo = Mock()
    conn_repo.get_by_site_and_moodle_user_id = AsyncMock()
    conn_repo.save = AsyncMock()

    with pytest.raises(RegistrationError):
        await _use_case(user_repo=user_repo, conn_repo=conn_repo, valid_token=False).execute(_input())

    user_repo.get_by_email.assert_not_awaited()
    conn_repo.get_by_site_and_moodle_user_id.assert_not_awaited()
