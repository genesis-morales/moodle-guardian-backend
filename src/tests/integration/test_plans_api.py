import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

pytestmark = pytest.mark.anyio


async def test_list_plans_returns_catalog_for_the_web():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/plans")

    assert response.status_code == 200
    plans = {p["key"]: p for p in response.json()["plans"]}
    assert set(plans) == {"alerta", "escudo", "guardian"}

    # La web pinta precio + canales (con label) desde aquí: contrato estable.
    assert plans["escudo"]["price_crc"] == 2000
    guardian_channels = {c["key"] for c in plans["guardian"]["channels"]}
    assert {"whatsapp", "telegram", "email", "calendar", "notion"} == guardian_channels
    # Cada canal trae label para la UI.
    assert all(c["label"] for c in plans["guardian"]["channels"])
