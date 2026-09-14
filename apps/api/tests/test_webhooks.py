import json

import pytest
from tests.conftest import sign, webhook_payload


@pytest.mark.asyncio
async def test_health(app_client) -> None:
    client, *_ = app_client
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(app_client) -> None:
    client, *_ = app_client
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] is True
    assert body["ai_required_for_readiness"] is False


@pytest.mark.asyncio
async def test_webhook_requires_signature(app_client) -> None:
    client, *_ = app_client
    response = await client.post("/webhooks/gitea", json=webhook_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(app_client) -> None:
    client, *_ = app_client
    body = json.dumps(webhook_payload()).encode()
    response = await client.post(
        "/webhooks/gitea",
        content=body,
        headers={"X-Gitea-Signature": "sha256=deadbeef", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_webhook(app_client) -> None:
    client, *_ = app_client
    body = b'{"action": 123, "pull_request": "nope"}'
    response = await client.post(
        "/webhooks/gitea",
        content=body,
        headers={"X-Gitea-Signature": sign(body), "Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_valid_webhook_is_accepted(app_client) -> None:
    client, processor, gitea, ai = app_client
    body = json.dumps(webhook_payload("opened")).encode()
    response = await client.post(
        "/webhooks/gitea",
        content=body,
        headers={
            "X-Gitea-Signature": sign(body),
            "X-Gitea-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    listed = await client.get("/api/prs")
    assert listed.status_code == 200
    assert listed.json()[0]["number"] == 42
    assert any(call[0] == "create_comment" for call in gitea.calls)
    assert "approved" not in gitea.comments[0]["body"].lower()
    assert "Merge authority" not in gitea.comments[0]["body"]
    assert "Automated PR Review" in gitea.comments[0]["body"]


@pytest.mark.asyncio
async def test_closed_webhook_is_ignored(app_client) -> None:
    client, _processor, gitea, _ai = app_client
    body = json.dumps(webhook_payload("closed")).encode()
    response = await client.post(
        "/webhooks/gitea",
        content=body,
        headers={
            "X-Gitea-Signature": sign(body),
            "X-Gitea-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    assert response.json() == {"status": "ignored"}
    listed = await client.get("/api/prs")
    assert listed.json() == []
    assert not any(call[0] == "create_comment" for call in gitea.calls)


@pytest.mark.asyncio
async def test_merged_webhook_is_ignored(app_client) -> None:
    client, *_ = app_client
    payload = webhook_payload("closed")
    payload["pull_request"]["merged"] = True
    payload["pull_request"]["state"] = "closed"
    body = json.dumps(payload).encode()
    response = await client.post(
        "/webhooks/gitea",
        content=body,
        headers={
            "X-Gitea-Signature": sign(body),
            "X-Gitea-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    assert response.json() == {"status": "ignored"}
    listed = await client.get("/api/prs")
    assert listed.json() == []
