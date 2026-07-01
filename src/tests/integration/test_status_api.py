from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from src.config.settings import get_settings
from src.domain.entities.scan_run import ScanFailure, ScanRun
from src.main import app

pytestmark = pytest.mark.anyio

TOKEN = "test-status-token"


@pytest.fixture
def configured_token():
    settings = get_settings()
    original = settings.cron_secret_token
    settings.cron_secret_token = TOKEN
    yield TOKEN
    settings.cron_secret_token = original


async def _get(token: str | None):
    headers = {"X-Cron-Token": token} if token is not None else {}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get("/v1/status", headers=headers)


async def test_missing_token_is_rejected(configured_token):
    response = await _get(token=None)
    assert response.status_code == 401


async def test_wrong_token_is_rejected(configured_token):
    response = await _get(token="nope")
    assert response.status_code == 401


async def test_disabled_when_token_not_configured():
    settings = get_settings()
    original = settings.cron_secret_token
    settings.cron_secret_token = None
    try:
        response = await _get(token="whatever")
    finally:
        settings.cron_secret_token = original
    assert response.status_code == 503


async def test_valid_token_returns_status(configured_token, monkeypatch):
    now = datetime.now(UTC)
    run = ScanRun(
        job_name="scan",
        started_at=now - timedelta(seconds=10),
        finished_at=now - timedelta(seconds=2),
        total_users=2,
        success_count=1,
        failure_count=1,
        failures=[ScanFailure(moodle_user_id=42, error="boom")],
    )

    user_repo = Mock()
    user_repo.list_active = AsyncMock(return_value=[object(), object()])
    run_repo = Mock()
    run_repo.list_recent = AsyncMock(return_value=[run])

    monkeypatch.setattr("src.api.v1.status.get_user_repository", lambda: user_repo)
    monkeypatch.setattr("src.api.v1.status.get_scan_run_repository", lambda: run_repo)

    response = await _get(configured_token)

    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "ok"
    assert body["active_users"] == 2
    assert body["last_scan"]["status"] == "partial"
    assert body["last_scan"]["failures"] == [{"moodle_user_id": 42, "error": "boom"}]
    assert len(body["recent_runs"]) == 1
