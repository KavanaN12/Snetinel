import pytest

from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_production_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        ready = await client.get("/readyz")
        live = await client.get("/livez")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert live.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.json()["status"] == "ready"
    assert live.json()["status"] == "alive"
