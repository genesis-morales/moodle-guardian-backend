import pytest

from src.domain.entities.subscription_plan import (
    CHANNEL_EMAIL,
    CHANNEL_NOTION,
    CHANNEL_TELEGRAM,
    CHANNEL_WHATSAPP,
    DEFAULT_PLAN_KEY,
    PLANS,
    UnknownPlanError,
    get_plan,
    is_valid_plan,
    plan_allows,
)


def test_catalog_has_the_three_product_plans():
    assert set(PLANS) == {"alerta", "escudo", "guardian"}


def test_default_plan_is_the_free_tier():
    assert DEFAULT_PLAN_KEY == "alerta"
    assert get_plan(DEFAULT_PLAN_KEY).price_crc == 0


def test_prices_match_product():
    assert get_plan("alerta").price_crc == 0
    assert get_plan("escudo").price_crc == 2000
    assert get_plan("guardian").price_crc == 4000


def test_plan_channels_are_a_ceiling_that_grows_by_tier():
    # Cada tier incluye estrictamente más canales que el anterior.
    alerta = set(get_plan("alerta").channels)
    escudo = set(get_plan("escudo").channels)
    guardian = set(get_plan("guardian").channels)
    assert alerta < escudo < guardian
    assert alerta == {CHANNEL_TELEGRAM}
    assert CHANNEL_EMAIL in escudo
    assert {CHANNEL_WHATSAPP, CHANNEL_NOTION} <= guardian


def test_plan_allows_checks_membership():
    assert plan_allows("alerta", CHANNEL_TELEGRAM) is True
    # WhatsApp/Notion NO están en el free tier: base del gating por canal (feat 3).
    assert plan_allows("alerta", CHANNEL_WHATSAPP) is False
    assert plan_allows("guardian", CHANNEL_NOTION) is True


def test_get_plan_unknown_raises():
    assert is_valid_plan("nope") is False
    with pytest.raises(UnknownPlanError):
        get_plan("nope")
