import pytest
from pydantic import ValidationError

from src.api.dependencies import (
    _email_channel_notifier_for,
    _moodle_gateway_for,
    _telegram_channel_notifier_for,
)
from src.config.settings import Settings
from src.infrastructure.external.brevo.brevo_email_notifier import BrevoEmailNotifier
from src.infrastructure.external.moodle.fake_moodle_client import FakeMoodleClient
from src.infrastructure.external.moodle.moodle_client import MoodleClient
from src.infrastructure.external.telegram.telegram_channel_notifier import (
    TelegramChannelNotifier,
)
from src.infrastructure.notifications.fake_channel_notifier import FakeChannelNotifier

_DB = "postgresql+asyncpg://u:p@localhost:5432/db"


def _settings(**overrides) -> Settings:
    # _env_file=None: no cargar el .env real para aislar el test.
    return Settings(_env_file=None, database_url=_DB, **overrides)


def test_moodle_gateway_fake_only_in_local():
    assert isinstance(_moodle_gateway_for("local"), FakeMoodleClient)
    assert isinstance(_moodle_gateway_for("dev"), MoodleClient)
    assert isinstance(_moodle_gateway_for("prod"), MoodleClient)


def test_telegram_channel_notifier_selected_by_use_fake_flag():
    # Los factories de canal reciben el bool `use_fake`: la decisión real/fake vive
    # en settings (use_fake_notifier / use_fake_email).
    assert isinstance(_telegram_channel_notifier_for(False), TelegramChannelNotifier)
    assert isinstance(_telegram_channel_notifier_for(True), FakeChannelNotifier)


def test_email_channel_notifier_selected_by_use_fake_flag():
    assert isinstance(_email_channel_notifier_for(False), BrevoEmailNotifier)
    assert isinstance(_email_channel_notifier_for(True), FakeChannelNotifier)


def test_profile_properties():
    assert _settings(environment="local").use_fake_moodle is True
    assert _settings(environment="dev").use_fake_moodle is False
    assert _settings(environment="dev").use_fake_notifier is True
    assert _settings(environment="prod", telegram_bot_token="x").use_fake_notifier is False


def test_email_is_fake_unless_opted_in():
    # El email arranca fake SIEMPRE (incluso prod) salvo opt-in explícito, para no
    # exigir credenciales Brevo donde no existen.
    assert _settings(environment="prod", telegram_bot_token="x").use_fake_email is True
    assert _settings(environment="local").use_fake_email is True
    s = _settings(
        use_fake_email_override=False,
        brevo_api_key="k",
        brevo_sender_email="no-reply@campusguardian.app",
    )
    assert s.use_fake_email is False


def test_real_email_requires_brevo_credentials():
    # USE_FAKE_EMAIL=false sin credenciales Brevo debe fallar-rápido.
    with pytest.raises(ValidationError):
        _settings(use_fake_email_override=False, brevo_api_key=None)


def test_use_fake_notifier_override_decouples_from_environment():
    # Override=false en local => notifier real (con token), Moodle sigue fake.
    s = _settings(
        environment="local",
        use_fake_notifier_override=False,
        telegram_bot_token="x",
    )
    assert s.use_fake_notifier is False
    assert s.use_fake_moodle is True  # el override no toca el Moodle

    # Override=true en prod => fuerza notifier fake aunque sea prod.
    s2 = _settings(
        environment="prod",
        use_fake_notifier_override=True,
        telegram_bot_token="x",
    )
    assert s2.use_fake_notifier is True


def test_real_notifier_override_requires_token():
    # USE_FAKE_NOTIFIER=false sin token debe fallar-rápido, igual que prod.
    with pytest.raises(ValidationError):
        _settings(
            environment="local",
            use_fake_notifier_override=False,
            telegram_bot_token=None,
        )


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError):
        _settings(environment="production")


def test_prod_requires_telegram_token():
    with pytest.raises(ValidationError):
        _settings(environment="prod", telegram_bot_token=None)
    # Con token, arranca.
    assert _settings(environment="prod", telegram_bot_token="x").environment == "prod"


def test_environment_is_normalized():
    assert _settings(environment="LOCAL").environment == "local"
