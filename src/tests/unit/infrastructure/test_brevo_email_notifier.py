"""Tests de BrevoEmailNotifier (adapter HTTP del canal email).

Mockea httpx (no pega a la red): verifica la forma del payload que Brevo espera
(`sender`/`to`/`subject`/`htmlContent`), el header `api-key`, el fail-fast sin
credenciales, y que un error HTTP se propague (vía raise_for_status).
"""

import httpx
import pytest

import src.infrastructure.external.brevo.brevo_email_notifier as brevo_module
from src.config.settings import Settings
from src.infrastructure.external.brevo.brevo_email_notifier import BrevoEmailNotifier

pytestmark = pytest.mark.anyio

_DB = "postgresql+asyncpg://u:p@localhost:5432/db"


def _settings(**overrides) -> Settings:
    base = dict(
        database_url=_DB,
        brevo_api_key="secret-key",
        brevo_sender_email="no-reply@campusguardian.app",
        brevo_sender_name="CampusGuardian",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


class _FakeResponse:
    def __init__(self, *, raise_exc: Exception | None = None) -> None:
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc is not None:
            raise self._raise_exc


class _FakeAsyncClient:
    """Captura la llamada .post() en `calls` (compartido) y devuelve la respuesta fija."""

    def __init__(self, calls: list, response: _FakeResponse) -> None:
        self._calls = calls
        self._response = response

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def post(self, url, json=None, headers=None) -> _FakeResponse:
        self._calls.append({"url": url, "json": json, "headers": headers})
        return self._response


def _patch_httpx(monkeypatch, calls: list, response: _FakeResponse) -> None:
    monkeypatch.setattr(
        brevo_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(calls, response),
    )


def _notifier(**settings_overrides) -> BrevoEmailNotifier:
    notifier = BrevoEmailNotifier()
    notifier.settings = _settings(**settings_overrides)
    return notifier


async def test_posts_expected_payload_and_headers(monkeypatch):
    calls: list = []
    _patch_httpx(monkeypatch, calls, _FakeResponse())

    await _notifier().deliver("student@correo.com", "Asunto", "<p>Hola</p>")

    assert len(calls) == 1
    call = calls[0]
    assert call["url"].endswith("/smtp/email")
    assert call["json"]["sender"] == {
        "email": "no-reply@campusguardian.app",
        "name": "CampusGuardian",
    }
    assert call["json"]["to"] == [{"email": "student@correo.com"}]
    assert call["json"]["subject"] == "Asunto"
    assert call["json"]["htmlContent"] == "<p>Hola</p>"
    assert call["headers"]["api-key"] == "secret-key"


async def test_subject_falls_back_to_sender_name_when_none(monkeypatch):
    calls: list = []
    _patch_httpx(monkeypatch, calls, _FakeResponse())

    await _notifier().deliver("student@correo.com", None, "<p>x</p>")

    assert calls[0]["json"]["subject"] == "CampusGuardian"


async def test_uses_configured_api_base_url(monkeypatch):
    calls: list = []
    _patch_httpx(monkeypatch, calls, _FakeResponse())

    await _notifier(brevo_api_base_url="https://api.example.com/v9").deliver(
        "s@c.com", "s", "b"
    )

    assert calls[0]["url"] == "https://api.example.com/v9/smtp/email"


async def test_raises_when_api_key_missing(monkeypatch):
    # Sin credenciales no debe intentar la llamada HTTP (fail-fast local).
    calls: list = []
    _patch_httpx(monkeypatch, calls, _FakeResponse())

    notifier = _notifier()
    notifier.settings = _settings(brevo_api_key=None)

    with pytest.raises(ValueError):
        await notifier.deliver("s@c.com", "s", "b")
    assert calls == []


async def test_raises_when_sender_email_missing(monkeypatch):
    calls: list = []
    _patch_httpx(monkeypatch, calls, _FakeResponse())

    notifier = _notifier()
    notifier.settings = _settings(brevo_sender_email=None)

    with pytest.raises(ValueError):
        await notifier.deliver("s@c.com", "s", "b")
    assert calls == []


async def test_propagates_http_error(monkeypatch):
    # Un 4xx/5xx de Brevo (raise_for_status) se propaga para que el dispatcher lo
    # cuente como fallo de ese canal.
    err = httpx.HTTPStatusError("400", request=None, response=None)
    _patch_httpx(monkeypatch, [], _FakeResponse(raise_exc=err))

    with pytest.raises(httpx.HTTPStatusError):
        await _notifier().deliver("s@c.com", "s", "b")
