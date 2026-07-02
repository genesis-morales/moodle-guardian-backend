import pytest
from pydantic import ValidationError

from src.api.dependencies import _moodle_gateway_for, _notifier_for
from src.config.settings import Settings
from src.infrastructure.external.moodle.fake_moodle_client import FakeMoodleClient
from src.infrastructure.external.moodle.moodle_client import MoodleClient
from src.infrastructure.external.telegram.fake_notifier import FakeNotifier
from src.infrastructure.external.telegram.telegram_bot import TelegramBotNotifier

_DB = "postgresql+asyncpg://u:p@localhost:5432/db"


def _settings(**overrides) -> Settings:
    # _env_file=None: no cargar el .env real para aislar el test.
    return Settings(_env_file=None, database_url=_DB, **overrides)


def test_moodle_gateway_fake_only_in_local():
    assert isinstance(_moodle_gateway_for("local"), FakeMoodleClient)
    assert isinstance(_moodle_gateway_for("dev"), MoodleClient)
    assert isinstance(_moodle_gateway_for("prod"), MoodleClient)


def test_notifier_real_only_in_prod():
    assert isinstance(_notifier_for("prod"), TelegramBotNotifier)
    assert isinstance(_notifier_for("dev"), FakeNotifier)
    assert isinstance(_notifier_for("local"), FakeNotifier)


def test_profile_properties():
    assert _settings(environment="local").use_fake_moodle is True
    assert _settings(environment="dev").use_fake_moodle is False
    assert _settings(environment="dev").use_fake_notifier is True
    assert _settings(environment="prod", telegram_bot_token="x").use_fake_notifier is False


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
