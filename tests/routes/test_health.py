# backend/tests/routes/test_health.py

from httpx import AsyncClient

from app.core.config import settings


async def test_health_check(client: AsyncClient) -> None:
    """Test basic health check endpoint"""
    r = await client.get(f"{settings.API_V1_STR}/utils/health-check/")
    assert r.status_code == 200
    assert r.json() is True
