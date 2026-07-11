import pytest
from unittest.mock import AsyncMock, Mock

from src.domain.entities.channel_preference import ChannelPreference
from src.domain.entities.subscription_plan import CHANNEL_EMAIL, CHANNEL_TELEGRAM
from src.domain.entities.user import User
from src.infrastructure.notifications.channel_dispatch_notifier import (
    ChannelDispatchNotifier,
)

pytestmark = pytest.mark.anyio


def _user(plan: str = "escudo") -> User:
    return User(
        id=1, moodle_user_id=42, moodle_token="tok",
        email="a@b.com", telegram_chat_id="chat", plan=plan,
    )


def _pref(channel: str, *, address: str = "addr", enabled: bool = True) -> ChannelPreference:
    return ChannelPreference(
        id=None, account_id=1, channel=channel, address=address, is_enabled=enabled
    )


def _notifier() -> Mock:
    notifier = Mock()
    notifier.deliver = AsyncMock()
    return notifier


def _builder(rendered: str = "BODY") -> Mock:
    # El render recibe el builder del canal y devuelve el cuerpo ya renderizado.
    return Mock(name="builder", _rendered=rendered)


def _pref_repo(preferences: list[ChannelPreference]) -> Mock:
    repo = Mock()
    repo.list_by_account_id = AsyncMock(return_value=preferences)
    return repo


def _render(_builder) -> str:
    return "BODY"


async def test_delivers_to_enabled_channel_allowed_by_plan():
    notifier = _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([_pref(CHANNEL_TELEGRAM, address="chat")]),
        channels={CHANNEL_TELEGRAM: (notifier, _builder())},
    )

    delivered = await dispatcher.dispatch(_user(), _render, subject="Asunto")

    assert delivered is True
    notifier.deliver.assert_awaited_once_with("chat", "Asunto", "BODY")


async def test_fans_out_to_all_active_channels():
    tg, email = _notifier(), _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([
            _pref(CHANNEL_TELEGRAM, address="chat"),
            _pref(CHANNEL_EMAIL, address="a@b.com"),
        ]),
        channels={
            CHANNEL_TELEGRAM: (tg, _builder()),
            CHANNEL_EMAIL: (email, _builder()),
        },
    )

    delivered = await dispatcher.dispatch(_user(plan="escudo"), _render, subject="s")

    assert delivered is True
    tg.deliver.assert_awaited_once()
    email.deliver.assert_awaited_once()


async def test_skips_channel_not_allowed_by_plan():
    # Plan alerta solo permite telegram: la pref de email, aunque habilitada, se ignora.
    email = _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([_pref(CHANNEL_EMAIL, address="a@b.com")]),
        channels={CHANNEL_EMAIL: (email, _builder())},
    )

    delivered = await dispatcher.dispatch(_user(plan="alerta"), _render, subject="s")

    assert delivered is False
    email.deliver.assert_not_awaited()


async def test_skips_disabled_preference():
    tg = _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([
            _pref(CHANNEL_TELEGRAM, address="chat", enabled=False)
        ]),
        channels={CHANNEL_TELEGRAM: (tg, _builder())},
    )

    delivered = await dispatcher.dispatch(_user(), _render, subject="s")

    assert delivered is False
    tg.deliver.assert_not_awaited()


async def test_ignores_channel_without_registered_adapter():
    # WhatsApp está permitido por guardian y habilitado, pero no hay adapter cableado:
    # se ignora en silencio (no revienta el fan-out).
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([_pref("whatsapp", address="+506")]),
        channels={},  # sin adapters registrados
    )

    delivered = await dispatcher.dispatch(_user(plan="guardian"), _render, subject="s")

    assert delivered is False


async def test_best_effort_one_channel_fails_other_delivers():
    # Un canal falla; el otro entrega -> la notificación se da por hecha (True), sin
    # propagar la excepción (así no se re-notifica por TODOS los canales).
    tg = _notifier()
    tg.deliver.side_effect = RuntimeError("telegram caído")
    email = _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([
            _pref(CHANNEL_TELEGRAM, address="chat"),
            _pref(CHANNEL_EMAIL, address="a@b.com"),
        ]),
        channels={
            CHANNEL_TELEGRAM: (tg, _builder()),
            CHANNEL_EMAIL: (email, _builder()),
        },
    )

    delivered = await dispatcher.dispatch(_user(plan="escudo"), _render, subject="s")

    assert delivered is True
    email.deliver.assert_awaited_once()


async def test_raises_when_all_channels_fail():
    # Hay destinos pero TODOS fallan -> se propaga (el scan no guarda snapshot y reintenta).
    tg = _notifier()
    tg.deliver.side_effect = RuntimeError("caído")
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([_pref(CHANNEL_TELEGRAM, address="chat")]),
        channels={CHANNEL_TELEGRAM: (tg, _builder())},
    )

    with pytest.raises(RuntimeError):
        await dispatcher.dispatch(_user(), _render, subject="s")


async def test_returns_false_without_touching_notifiers_when_no_preferences():
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([]),
        channels={CHANNEL_TELEGRAM: (_notifier(), _builder())},
    )

    delivered = await dispatcher.dispatch(_user(), _render, subject="s")

    assert delivered is False


async def test_render_receives_the_channel_specific_builder():
    # El dispatcher arma el cuerpo con el builder de ESE canal: cada notifier recibe lo
    # que su propio builder renderizó (base del multi-canal: HTML email ≠ HTML telegram).
    tg_builder, email_builder = _builder(), _builder()
    tg, email = _notifier(), _notifier()
    dispatcher = ChannelDispatchNotifier(
        channel_preference_repository=_pref_repo([
            _pref(CHANNEL_TELEGRAM, address="chat"),
            _pref(CHANNEL_EMAIL, address="a@b.com"),
        ]),
        channels={
            CHANNEL_TELEGRAM: (tg, tg_builder),
            CHANNEL_EMAIL: (email, email_builder),
        },
    )

    seen: list = []

    def render(builder):
        seen.append(builder)
        return "BODY"

    await dispatcher.dispatch(_user(plan="escudo"), render, subject="s")

    assert set(map(id, seen)) == {id(tg_builder), id(email_builder)}
