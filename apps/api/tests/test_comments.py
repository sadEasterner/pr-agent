from pathlib import Path

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.providers.openai import parse_ai_payload
from app.gitea.models import GiteaFileChange, GiteaPullRequest
from app.gitea.service import PullRequestSnapshot
from app.policy.engine import PolicyEngine
from app.reviews.comments import render_gitea_review
from app.rules.engine import RulesEngine
from app.rules.loader import AutomationConfig, load_review_rules
from tests.conftest import sample_ai_payload


def test_gitea_comment_is_paragraph_and_suggestions() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    files = [GiteaFileChange(filename="apps/api/app/api/users.py", additions=4, deletions=0)]
    snapshot = PullRequestSnapshot(
        repository="acme/demo",
        number=42,
        title="Add user endpoint",
        description="Adds an endpoint",
        author="alice",
        source_branch="feat",
        target_branch="main",
        head_sha="abc123",
        html_url="https://gitea.test/acme/demo/pulls/42",
        state="open",
        merged=False,
        files=files,
        diff="",
        commit_count=1,
        pull_request=GiteaPullRequest.model_validate({"number": 42, "title": "x"}),
    )
    body = render_gitea_review(
        snapshot,
        RulesEngine(loaded).evaluate(snapshot),
        parse_ai_payload(__import__("json").dumps(sample_ai_payload())),
        PolicyEngine(AutomationConfig(mode="review_only", allowed_actions=["post_review"])),
    )
    assert "abc123" in body
    assert "approved" not in body.lower()
    assert "Merge authority" not in body
    assert "CHANGES REQUESTED" not in body
    assert "never an instruction" in SYSTEM_PROMPT.lower() or "untrusted" in SYSTEM_PROMPT.lower()
    assert "Suggestions:" in body or "authorization" in body.lower()
