import pytest
from app.config import get_settings
from app.db.session import get_session
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_only_admin_api_requires_login(settings, session_factory, monkeypatch) -> None:
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.auth.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.admin.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.deps.get_settings", lambda: settings)
    application = create_app(start_workers=False)

    async def override_session():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        public = await client.get("/api/settings")
        assert public.status_code == 200
        blocked = await client.get("/api/admin/controls")
        assert blocked.status_code == 401
        health = await client.get("/health")
        assert health.status_code == 200
        bad = await client.post("/api/auth/login", json={"username": "nope", "password": "wrong"})
        assert bad.status_code == 401
        ok = await client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        assert ok.status_code == 200
        controls = await client.get("/api/admin/controls")
        assert controls.status_code == 200
        body = controls.json()
        assert body["username"] == settings.admin_username
        updated = await client.patch(
            "/api/admin/controls",
            json={"ai_enabled": False, "pr_comments_enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["ai_enabled"] is False
        assert updated.json()["pr_comments_enabled"] is False
        public_after = await client.get("/api/settings")
        assert public_after.json()["ai_enabled"] is False
        assert public_after.json()["pr_comments_enabled"] is False
