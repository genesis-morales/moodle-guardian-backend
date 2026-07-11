from src.domain.entities.channel_preference import ChannelPreference
from src.domain.entities.subscription_plan import CHANNEL_EMAIL, CHANNEL_TELEGRAM


def make(channel: str = CHANNEL_TELEGRAM, address: str = "123", enabled: bool = True):
    return ChannelPreference(
        id=None, account_id=1, channel=channel, address=address, is_enabled=enabled
    )


def test_enable_sets_address_and_flag():
    pref = make(channel=CHANNEL_EMAIL, address="", enabled=False)
    pref.enable("estudiante@uned.ac.cr")
    assert pref.is_enabled is True
    assert pref.address == "estudiante@uned.ac.cr"


def test_disable_keeps_address_but_turns_off():
    pref = make(address="1297978506")
    pref.disable()
    assert pref.is_enabled is False
    assert pref.address == "1297978506"  # la dirección se conserva, solo se apaga
