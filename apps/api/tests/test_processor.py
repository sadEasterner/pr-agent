import json

import pytest
from app.db.models import Review, WebhookEvent
from app.webhooks.schemas import GiteaWebhookEvent
from sqlalchemy import select
from tests.conftest import sign, webhook_payload


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_create_second_review(app_client, session) -> None:
    client, *_ = app_client
    body = json.dumps(webhook_payload("opened", "abc123")).encode()
    headers = {
        "X-Gitea-Signature": sign(body),
        "X-Gitea-Event": "pull_request",
        "Content-Type": "application/json",
    }
    first = await client.post("/webhooks/gitea", content=body, headers=headers)
    second = await client.post("/webhooks/gitea", content=body, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    reviews = (await session.execute(select(Review))).scalars().all()
    events = (await session.execute(select(WebhookEvent))).scalars().all()
    assert len(reviews) == 1
    assert len(events) == 1


@pytest.mark.asyncio
async def test_same_sha_is_not_reviewed_twice(app_client) -> None:
    client, processor, *_ = app_client
    first = GiteaWebhookEvent.model_validate(webhook_payload("opened", "abc123"))
    second = GiteaWebhookEvent.model_validate(webhook_payload("edited", "abc123"))
    await processor.process(first)
    await processor.process(second)
    listed = await client.get("/api/prs/acme/demo/42")
    assert listed.status_code == 200
    assert listed.json()["review_iterations"] == 1


@pytest.mark.asyncio
async def test_new_sha_creates_new_review_iteration(app_client, fake_gitea) -> None:
    client, processor, *_ = app_client
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("opened", "abc123")))
    fake_gitea.pr.head.sha = "def456"
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("synchronized", "def456")))
    detail = await client.get("/api/prs/acme/demo/42")
    body = detail.json()
    assert body["review_iterations"] == 2
    assert body["reviews"][0]["commit_sha"] == "abc123"
    assert body["reviews"][1]["commit_sha"] == "def456"
    assert body["merge_authority"] == "human_approval_required"
    assert body["human_review_status"] in {"changes_requested", "high_risk", "waiting_for_human"}


@pytest.mark.asyncio
async def test_gitea_failure_is_logged_not_raised(settings, session_factory, fake_ai) -> None:
    from app.ai.reviewer import AiReviewer
    from app.jobs.processor import ReviewProcessor
    from app.rules.loader import load_review_rules
    from tests.conftest import FakeGiteaClient

    gitea = FakeGiteaClient(settings)
    gitea.fail_get_pr = True
    loaded = load_review_rules(settings.config_dir)
    processor = ReviewProcessor(
        settings,
        session_factory,
        loaded,
        gitea,
        ai_reviewer=AiReviewer(settings, loaded, fake_ai),
    )
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload()))
    assert any(call[0] == "get_pull_request" for call in gitea.calls)


@pytest.mark.asyncio
async def test_ai_failure_still_persists_review(app_client, fake_ai) -> None:
    client, processor, *_ = app_client
    fake_ai.error = RuntimeError("provider down")
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("opened", "abc123")))
    detail = await client.get("/api/prs/acme/demo/42")
    assert detail.status_code == 200
    assert detail.json()["latest_recommendation"] == "unable_to_review"
    assert detail.json()["human_review_status"] == "unable_to_review"


@pytest.mark.asyncio
async def test_processor_skips_closed_pull_request(app_client, fake_gitea) -> None:
    client, processor, *_ = app_client
    fake_gitea.pr.state = "closed"
    fake_gitea.pr.merged = False
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("edited", "abc123")))
    listed = await client.get("/api/prs")
    assert listed.json() == []
    assert not any(call[0] == "create_comment" for call in fake_gitea.calls)


@pytest.mark.asyncio
async def test_admin_can_disable_pr_comments(app_client, fake_gitea, settings) -> None:
    client, processor, *_ = app_client
    login = await client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login.status_code == 200
    toggled = await client.patch("/api/admin/controls", json={"pr_comments_enabled": False})
    assert toggled.status_code == 200
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("opened", "abc123")))
    assert not any(call[0] == "create_comment" for call in fake_gitea.calls)
    assert not fake_gitea.comments


@pytest.mark.asyncio
async def test_admin_can_disable_ai_review(app_client, fake_ai, settings) -> None:
    client, processor, *_ = app_client
    login = await client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login.status_code == 200
    await client.patch("/api/admin/controls", json={"ai_enabled": False})
    await processor.process(GiteaWebhookEvent.model_validate(webhook_payload("opened", "abc123")))
    detail = await client.get("/api/prs/acme/demo/42")
    assert detail.status_code == 200
    assert "AI review was disabled" in detail.json()["reviews"][0]["summary"]
    assert fake_ai.prompts == []
