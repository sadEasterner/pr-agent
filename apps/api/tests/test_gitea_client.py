
import httpx
import pytest
from app.gitea.client import GiteaClient, GiteaClientError
from tests.conftest import sample_pr_payload


@pytest.mark.asyncio
async def test_gitea_client_get_pr(settings) -> None:
    payload = sample_pr_payload()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload)
        ),
        base_url=settings.gitea_base_url,
    ) as client:
        gitea = GiteaClient(settings, client=client)
        pr = await gitea.get_pull_request("acme/demo", 42)
        assert pr.number == 42
        assert pr.head.sha == "abc123"


@pytest.mark.asyncio
async def test_gitea_client_changed_files(settings) -> None:
    files = [{"filename": "app/main.py", "additions": 3, "deletions": 1, "status": "modified"}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/pulls/42/files")
        return httpx.Response(200, json=files)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=settings.gitea_base_url,
    ) as client:
        gitea = GiteaClient(settings, client=client)
        changed = await gitea.get_changed_files("acme/demo", 42)
        assert changed[0].filename == "app/main.py"


@pytest.mark.asyncio
async def test_gitea_client_http_error(settings) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(500, json={"message": "fail"})),
        base_url=settings.gitea_base_url,
    ) as client:
        gitea = GiteaClient(settings, client=client)
        with pytest.raises(GiteaClientError):
            await gitea.get_repository("acme/demo")


@pytest.mark.asyncio
async def test_gitea_client_does_not_spread_raw_calls(settings) -> None:
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/comments"):
            return httpx.Response(201, json={"id": 1, "body": "ok"})
        if request.url.path.endswith("/labels"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/requested_reviewers"):
            return httpx.Response(201, json={})
        if request.url.path.endswith(".diff"):
            return httpx.Response(200, text="diff")
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[{"sha": "abc"}])
        if "/statuses/" in request.url.path:
            return httpx.Response(200, json=[{"status": "success"}])
        return httpx.Response(200, json={"id": 1, "name": "demo", "full_name": "acme/demo"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=settings.gitea_base_url,
    ) as client:
        gitea = GiteaClient(settings, client=client)
        await gitea.get_repository("acme/demo")
        await gitea.get_diff("acme/demo", 1)
        await gitea.get_commits("acme/demo", 1)
        await gitea.get_statuses("acme/demo", "abc")
        await gitea.create_comment("acme/demo", 1, "hello")
        await gitea.add_labels("acme/demo", 1, ["backend"])
        await gitea.request_reviewers("acme/demo", 1, ["backend-lead"])
    assert any("/api/v1/repos/acme/demo" in item for item in captured)
