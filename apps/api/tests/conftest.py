from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from app.config import Settings, get_settings
from app.db.base import Base
from app.db.models import Finding, PullRequest, Review, ReviewMetrics
from app.db.session import get_session
from app.gitea.client import GiteaClient
from app.gitea.models import GiteaFileChange, GiteaPullRequest
from app.jobs.processor import ReviewProcessor
from app.main import create_app
from app.rules.loader import load_review_rules
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TEST_SECRET = "test-webhook-secret"
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite://",
        gitea_base_url="https://gitea.test",
        gitea_token="test-token",
        gitea_webhook_secret=TEST_SECRET,
        ai_enabled=True,
        ai_provider="openai",
        ai_model="mock-model",
        openai_api_key="sk-test",
        config_dir=CONFIG_DIR,
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
async def session_factory(settings: Settings) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest.fixture
async def session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as db_session:
        yield db_session


class FakeGiteaClient(GiteaClient):
    def __init__(self, settings: Settings, snapshot: dict[str, Any] | None = None) -> None:
        self._settings = settings
        self.calls: list[tuple[str, Any]] = []
        self.comments: list[dict[str, Any]] = []
        self.labels: list[str] = []
        self.fail_get_pr = False
        data = snapshot or sample_pr_payload()
        self.pr = GiteaPullRequest.model_validate(data)
        self.files = [
            GiteaFileChange(
                filename="apps/api/app/api/users.py",
                status="modified",
                additions=12,
                deletions=2,
                changes=14,
                patch="@@ -80,6 +80,10 @@\n+def get_user():\n+    return db.get(1)\n",
            ),
            GiteaFileChange(
                filename="apps/api/tests/test_users.py",
                status="added",
                additions=8,
                deletions=0,
                changes=8,
                patch="@@ -0,0 +1,8 @@\n+def test_get_user():\n+    assert True\n",
            ),
        ]
        self.diff = "diff --git a/apps/api/app/api/users.py b/apps/api/app/api/users.py\n+def get_user():\n"
        self.commits = [{"sha": self.pr.head.sha if self.pr.head else "abc123", "commit": {"message": "feat"}}]

    async def close(self) -> None:
        return None

    async def get_pull_request(self, repository: str, number: int) -> GiteaPullRequest:
        self.calls.append(("get_pull_request", repository, number))
        if self.fail_get_pr:
            from app.gitea.client import GiteaClientError

            raise GiteaClientError("Gitea unavailable", status_code=500)
        return self.pr

    async def get_changed_files(self, repository: str, number: int) -> list[GiteaFileChange]:
        self.calls.append(("get_changed_files", repository, number))
        return self.files

    async def get_diff(self, repository: str, number: int) -> str:
        self.calls.append(("get_diff", repository, number))
        return self.diff

    async def get_commits(self, repository: str, number: int) -> list[Any]:
        from app.gitea.models import GiteaCommit

        self.calls.append(("get_commits", repository, number))
        return [GiteaCommit(sha="abc123", message="feat")]

    async def get_comments(self, repository: str, number: int) -> list[Any]:
        from app.gitea.models import GiteaComment

        return [GiteaComment.model_validate(item) for item in self.comments]

    async def create_comment(self, repository: str, number: int, body: str) -> Any:
        from app.gitea.models import GiteaComment

        self.calls.append(("create_comment", body))
        comment = {"id": len(self.comments) + 1, "body": body}
        self.comments.append(comment)
        return GiteaComment.model_validate(comment)

    async def update_comment(self, repository: str, comment_id: int, body: str) -> Any:
        from app.gitea.models import GiteaComment

        self.calls.append(("update_comment", comment_id, body))
        for comment in self.comments:
            if comment["id"] == comment_id:
                comment["body"] = body
        return GiteaComment(id=comment_id, body=body)

    async def add_labels(self, repository: str, number: int, labels: list[str]) -> None:
        self.labels.extend(labels)

    async def request_reviewers(self, repository: str, number: int, reviewers: list[str]) -> None:
        self.calls.append(("request_reviewers", reviewers))


class FakeAiProvider:
    name = "fake"

    def __init__(self, payload: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.payload = payload or sample_ai_payload()
        self.error = error
        self.prompts: list[tuple[str, str]] = []

    async def complete_review(self, system_prompt: str, user_prompt: str) -> Any:
        from app.ai.providers.openai import parse_ai_payload

        self.prompts.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return parse_ai_payload(json.dumps(self.payload))


def sample_pr_payload(sha: str = "abc123") -> dict[str, Any]:
    return {
        "number": 42,
        "title": "Add user endpoint",
        "body": "This pull request adds a user lookup endpoint with tests.",
        "state": "open",
        "html_url": "https://gitea.test/acme/demo/pulls/42",
        "merged": False,
        "created_at": datetime.now(UTC).isoformat(),
        "user": {"login": "alice"},
        "head": {"ref": "feature/users", "sha": sha},
        "base": {"ref": "main", "sha": "base123"},
    }


def sample_ai_payload() -> dict[str, Any]:
    return {
        "risk": "medium",
        "recommendation": "changes_requested",
        "summary": "One authorization issue should be resolved before merging.",
        "findings": [
            {
                "severity": "high",
                "confidence": 0.94,
                "file": "apps/api/app/api/users.py",
                "line": 82,
                "category": "authorization",
                "rule": "Every endpoint must verify authorization.",
                "message": "The new endpoint does not check the current user's permission.",
                "suggested_fix": "Use the existing permission guard before retrieving the user.",
            }
        ],
    }


def webhook_payload(action: str = "opened", sha: str = "abc123") -> dict[str, Any]:
    return {
        "action": action,
        "number": 42,
        "pull_request": sample_pr_payload(sha),
        "repository": {"full_name": "acme/demo", "name": "demo", "owner": {"login": "acme"}},
        "sender": {"login": "alice"},
    }


def sign(body: bytes, secret: str = TEST_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def fake_gitea(settings: Settings) -> FakeGiteaClient:
    return FakeGiteaClient(settings)


@pytest.fixture
def fake_ai() -> FakeAiProvider:
    return FakeAiProvider()


@pytest.fixture
async def app_client(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    fake_gitea: FakeGiteaClient,
    fake_ai: FakeAiProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[tuple[AsyncClient, ReviewProcessor, FakeGiteaClient, FakeAiProvider], None]:
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    loaded = load_review_rules(settings.config_dir)
    from app.ai.reviewer import AiReviewer

    processor = ReviewProcessor(
        settings,
        session_factory,
        loaded,
        fake_gitea,
        ai_reviewer=AiReviewer(settings, loaded, fake_ai),
    )

    class ImmediateQueue:
        async def enqueue(self, event: Any) -> None:
            await processor.process(event)

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    application = create_app(start_workers=False)
    application.state.job_queue = ImmediateQueue()
    application.state.processor = processor
    application.dependency_overrides[get_session] = _session_override(session_factory)
    application.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, processor, fake_gitea, fake_ai


def _session_override(factory: async_sessionmaker[AsyncSession]):
    async def override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    return override


async def seed_pr(session: AsyncSession, sha: str = "abc123") -> PullRequest:
    pull_request = PullRequest(
        repository="acme/demo",
        number=42,
        title="Add user endpoint",
        author="alice",
        description="Meaningful description for the change.",
        source_branch="feature/users",
        target_branch="main",
        gitea_url="https://gitea.test/acme/demo/pulls/42",
        latest_sha=sha,
        status="open",
        human_review_status="waiting_for_human",
        latest_risk="low",
        latest_recommendation="ready_for_human_review",
        opened_at=datetime.now(UTC),
    )
    session.add(pull_request)
    await session.flush()
    review = Review(
        pull_request_id=pull_request.id,
        commit_sha=sha,
        ai_model="mock-model",
        risk="low",
        recommendation="ready_for_human_review",
        summary="Looks reasonable.",
        processing_duration_ms=12,
        rules_result={},
        ai_enabled=True,
    )
    session.add(review)
    await session.flush()
    session.add(
        Finding(
            review_id=review.id,
            severity="medium",
            confidence=0.81,
            category="authorization",
            rule="Every endpoint must verify authorization.",
            file_path="apps/api/app/api/users.py",
            line=82,
            message="Check permissions.",
            suggested_fix="Add a guard.",
        )
    )
    session.add(
        ReviewMetrics(
            review_id=review.id,
            changed_files=2,
            lines_added=20,
            lines_removed=2,
            test_files_changed=1,
            number_of_commits=1,
        )
    )
    await session.commit()
    await session.refresh(pull_request)
    return pull_request
