from httpx import ASGITransport, AsyncClient
import pytest

from app.config import get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_login_required_for_api(settings, monkeypatch) -> None:
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.auth.get_settings", lambda: settings)
    application = create_app(start_workers=False)
    application.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        blocked = await client.get("/api/settings")
        assert blocked.status_code == 401
        health = await client.get("/health")
        assert health.status_code == 200
        me = await client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["authenticated"] is False
        bad = await client.post("/api/auth/login", json={"username": "nope", "password": "wrong"})
        assert bad.status_code == 401
        ok = await client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert ok.status_code == 200
        assert ok.json()["username"] == settings.admin_username
        allowed = await client.get("/api/settings")
        assert allowed.status_code == 200
        await client.post("/api/auth/logout")
        after = await client.get("/api/settings")
        assert after.status_code == 401
