import json

import httpx
import pytest
from app.scm.events import parse_webhook_event
from app.scm.factory import create_scm_provider
from app.scm.github import GitHubProvider
from app.scm.gitlab import GitLabProvider
from tests.conftest import sample_pr_payload, webhook_payload


def test_github_webhook_normalizes_synchronize() -> None:
    payload = webhook_payload("synchronize")
    event = parse_webhook_event("github", json.dumps(payload).encode())
    assert event.event_type == "synchronized"
    assert event.repository_name == "acme/demo"
    assert event.pr_number == 42


def test_gitlab_webhook_maps_merge_request() -> None:
    payload = {
        "object_kind": "merge_request",
        "user": {"username": "alice"},
        "project": {"path_with_namespace": "acme/demo", "name": "demo"},
        "object_attributes": {
            "iid": 42,
            "action": "open",
            "title": "Add user endpoint",
            "description": "Meaningful description for the change.",
            "url": "https://gitlab.example/acme/demo/-/merge_requests/42",
            "state": "opened",
            "source_branch": "feature/users",
            "target_branch": "main",
            "last_commit": {"id": "abc123"},
        },
    }
    event = parse_webhook_event("gitlab", json.dumps(payload).encode())
    assert event.event_type == "opened"
    assert event.repository_name == "acme/demo"
    assert event.head_sha == "abc123"
    assert event.is_closed_or_merged is False


def test_factory_selects_providers(settings) -> None:
    settings.scm_provider = "github"
    assert isinstance(create_scm_provider(settings), GitHubProvider)
    settings.scm_provider = "gitlab"
    assert isinstance(create_scm_provider(settings), GitLabProvider)
    settings.scm_provider = "gitea"
    provider = create_scm_provider(settings)
    assert provider.name == "gitea"


@pytest.mark.asyncio
async def test_github_provider_fetch_snapshot(settings) -> None:
    pr = sample_pr_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/pulls/42/files"):
            return httpx.Response(200, json=[{"filename": "app/main.py", "additions": 3, "deletions": 0, "status": "modified", "patch": "+x"}])
        if path.endswith("/pulls/42/commits"):
            return httpx.Response(200, json=[{"sha": "abc123"}])
        if path.endswith("/pulls/42") and request.headers.get("accept") == "application/vnd.github.diff":
            return httpx.Response(200, text="diff --git a/app/main.py")
        if path.endswith("/pulls/42"):
            return httpx.Response(200, json=pr)
        return httpx.Response(404, json={"message": path})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.com",
    ) as client:
        github = GitHubProvider(settings, client=client)
        snapshot = await github.fetch_snapshot("acme/demo", 42)
        assert snapshot.head_sha == "abc123"
        assert snapshot.author == "alice"
        assert snapshot.author_name == "Alice Example"
        assert snapshot.files[0].filename == "app/main.py"


@pytest.mark.asyncio
async def test_github_provider_upsert_comment(settings) -> None:
    comments: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/comments"):
            return httpx.Response(200, json=comments)
        if request.method == "POST" and request.url.path.endswith("/comments"):
            body = json.loads(request.content)
            comments.append({"id": 9, "body": body["body"]})
            return httpx.Response(201, json=comments[0])
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.com",
    ) as client:
        github = GitHubProvider(settings, client=client)
        await github.post_or_update_review_comment("acme/demo", 42, "first look")
        assert "PR-MANAGER-REVIEW" in str(comments[0]["body"])


@pytest.mark.asyncio
async def test_gitlab_provider_fetch_snapshot(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/changes"):
            return httpx.Response(
                200,
                json={"changes": [{"new_path": "app/main.py", "diff": "@@\n+x\n", "new_file": False}]},
            )
        if path.endswith("/commits"):
            return httpx.Response(200, json=[{"id": "abc123"}])
        if "/merge_requests/42" in path:
            return httpx.Response(
                200,
                json={
                    "iid": 42,
                    "title": "Add user endpoint",
                    "description": "desc",
                    "state": "opened",
                    "web_url": "https://gitlab.example/acme/demo/-/merge_requests/42",
                    "source_branch": "feature/users",
                    "target_branch": "main",
                    "sha": "abc123",
                    "author": {"username": "alice", "name": "Alice Example"},
                },
            )
        return httpx.Response(404, json={"message": path})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://gitlab.com/api/v4",
    ) as client:
        gitlab = GitLabProvider(settings, client=client)
        snapshot = await gitlab.fetch_snapshot("acme/demo", 42)
        assert snapshot.author == "alice"
        assert snapshot.author_name == "Alice Example"
        assert snapshot.html_url.endswith("/merge_requests/42")
        assert snapshot.files[0].filename == "app/main.py"
