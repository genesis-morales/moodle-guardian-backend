import pytest

from src.domain.entities.moodle_site import (
    MOODLE_SITES,
    UnknownMoodleSiteError,
    get_site,
    is_valid_site,
)


def test_catalog_has_aprende_and_educa():
    assert {"aprende", "educa"} <= set(MOODLE_SITES)


def test_get_site_returns_site_with_url():
    site = get_site("aprende")
    assert site.institution == "UNED"
    assert site.base_url.endswith("/webservice/rest/server.php")


def test_get_site_unknown_raises():
    with pytest.raises(UnknownMoodleSiteError):
        get_site("inexistente")


def test_is_valid_site():
    assert is_valid_site("educa") is True
    assert is_valid_site("nope") is False


def test_no_privileged_default():
    # Ningún sitio es 'default': no existe un DEFAULT_SITE_KEY exportado.
    import src.domain.entities.moodle_site as mod
    assert not hasattr(mod, "DEFAULT_SITE_KEY")
