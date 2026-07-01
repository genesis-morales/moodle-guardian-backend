import pytest

import src.infrastructure.external.moodle.http_client as http_client_module
from src.infrastructure.external.moodle.http_client import MoodleHttpClient
from src.domain.exceptions.domain_errors import MoodleTokenError

pytestmark = pytest.mark.anyio


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url, params=None) -> _FakeResponse:
        return _FakeResponse(self._payload)


def _patch_httpx(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(
        http_client_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(payload),
    )


async def test_call_raises_moodle_token_error_on_invalid_token(monkeypatch):
    _patch_httpx(
        monkeypatch,
        {
            "exception": "moodle_exception",
            "errorcode": "invalidtoken",
            "message": "Ficha (token) no válida - ficha no encontrada",
        },
    )

    client = MoodleHttpClient()

    with pytest.raises(MoodleTokenError, match="ficha no encontrada"):
        await client.call(token="bad", wsfunction="core_webservice_get_site_info")


async def test_call_raises_value_error_on_other_exception(monkeypatch):
    # Un error de Moodle distinto de token inválido NO debe tratarse como
    # MoodleTokenError (no debe desactivar al usuario).
    _patch_httpx(
        monkeypatch,
        {
            "exception": "moodle_exception",
            "errorcode": "somethingelse",
            "message": "Otro error de Moodle",
        },
    )

    client = MoodleHttpClient()

    with pytest.raises(ValueError, match="Otro error de Moodle") as exc_info:
        await client.call(token="x", wsfunction="whatever")
    assert not isinstance(exc_info.value, MoodleTokenError)


async def test_call_returns_data_on_success(monkeypatch):
    _patch_httpx(monkeypatch, {"userid": 3095, "sitename": "UNED"})

    client = MoodleHttpClient()

    data = await client.call(token="ok", wsfunction="core_webservice_get_site_info")
    assert data == {"userid": 3095, "sitename": "UNED"}
