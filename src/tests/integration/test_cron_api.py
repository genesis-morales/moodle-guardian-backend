from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1 import cron as cron_module
from src.config.settings import get_settings
from src.main import app

TOKEN = "test-cron-token"


@pytest.fixture
def configured_token():
    """Fija un token de cron en la settings cacheada y lo restaura al salir."""
    settings = get_settings()
    original = settings.cron_secret_token
    settings.cron_secret_token = TOKEN
    yield TOKEN
    settings.cron_secret_token = original


@pytest.fixture
def mocked_jobs(monkeypatch):
    """Reemplaza los jobs reales por AsyncMocks para no tocar Moodle/BD."""
    fakes = {name: AsyncMock() for name in cron_module.JOBS}
    monkeypatch.setattr(cron_module, "JOBS", fakes)
    return fakes


async def _post(job: str, token: str | None):
    headers = {"X-Cron-Token": token} if token is not None else {}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(f"/v1/cron/{job}", headers=headers)


@pytest.mark.anyio
async def test_valid_token_runs_job(configured_token, mocked_jobs):
    response = await _post("scan", configured_token)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "job": "scan"}
    mocked_jobs["scan"].assert_awaited_once()


@pytest.mark.anyio
async def test_missing_token_is_rejected(configured_token, mocked_jobs):
    response = await _post("scan", token=None)

    assert response.status_code == 401
    mocked_jobs["scan"].assert_not_awaited()


@pytest.mark.anyio
async def test_wrong_token_is_rejected(configured_token, mocked_jobs):
    response = await _post("scan", token="nope")

    assert response.status_code == 401
    mocked_jobs["scan"].assert_not_awaited()


@pytest.mark.anyio
async def test_unknown_job_returns_404(configured_token, mocked_jobs):
    response = await _post("does-not-exist", configured_token)

    assert response.status_code == 404
    for job in mocked_jobs.values():
        job.assert_not_awaited()


@pytest.mark.anyio
async def test_disabled_when_token_not_configured(mocked_jobs):
    settings = get_settings()
    original = settings.cron_secret_token
    settings.cron_secret_token = None
    try:
        response = await _post("scan", token="whatever")
    finally:
        settings.cron_secret_token = original

    assert response.status_code == 503
    mocked_jobs["scan"].assert_not_awaited()
