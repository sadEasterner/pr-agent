from pathlib import Path

from app.gitea.models import GiteaFileChange, GiteaPullRequest
from app.gitea.service import PullRequestSnapshot
from app.rules.engine import RulesEngine
from app.rules.loader import load_review_rules


def _snapshot(files: list[GiteaFileChange], description: str = "A complete description.") -> PullRequestSnapshot:
    pr = GiteaPullRequest.model_validate(
        {
            "number": 1,
            "title": "Test",
            "body": description,
            "head": {"ref": "feat", "sha": "abc"},
            "base": {"ref": "main", "sha": "def"},
            "user": {"login": "alice"},
        }
    )
    return PullRequestSnapshot(
        repository="acme/demo",
        number=1,
        title="Test",
        description=description,
        author="alice",
        author_name="Alice Example",
        source_branch="feat",
        target_branch="main",
        head_sha="abc",
        html_url="https://gitea.test/acme/demo/pulls/1",
        state="open",
        merged=False,
        files=files,
        diff="",
        commit_count=1,
        pull_request=pr,
    )


def test_missing_description() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    engine = RulesEngine(loaded)
    result = engine.evaluate(_snapshot([], description=""))
    assert result.missing_description is True
    assert any(item.rule == "require_description" for item in result.violations)


def test_large_pr_and_labels() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    engine = RulesEngine(loaded)
    files = [
        GiteaFileChange(filename="apps/dashboard/src/App.tsx", additions=400, deletions=20),
        GiteaFileChange(filename="apps/api/app/main.py", additions=200, deletions=10),
    ]
    result = engine.evaluate(_snapshot(files))
    assert result.large_pr is True
    assert "frontend" in result.labels
    assert "backend" in result.labels
    assert "frontend-lead" in result.suggested_reviewers
    assert "backend-lead" in result.suggested_reviewers


def test_dangerous_migration_and_test_paths() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    engine = RulesEngine(loaded)
    files = [
        GiteaFileChange(filename="docker-compose.yml", additions=4, deletions=0),
        GiteaFileChange(filename="migrations/0001.sql", additions=10, deletions=0),
        GiteaFileChange(filename="infra/main.tf", additions=5, deletions=0),
    ]
    result = engine.evaluate(_snapshot(files))
    assert result.dangerous_changes is True
    assert result.migration_changes is True
    assert result.infrastructure_changes is True
    assert result.test_changes is False
    assert "database" in result.labels


def test_workspace_isolation_blocks_other_apps_and_packages() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    engine = RulesEngine(loaded)
    mixed = engine.evaluate(
        _snapshot(
            [
                GiteaFileChange(filename="apps/app-one/src/index.ts", additions=4, deletions=0),
                GiteaFileChange(filename="apps/app-two/src/index.ts", additions=2, deletions=0),
            ]
        )
    )
    assert any(item.rule == "workspace_isolation" for item in mixed.violations)

    leaked_package = engine.evaluate(
        _snapshot(
            [
                GiteaFileChange(filename="apps/app-one/src/index.ts", additions=4, deletions=0),
                GiteaFileChange(filename="packages/package-one/src/index.ts", additions=2, deletions=0),
            ]
        )
    )
    assert any(item.rule == "workspace_isolation" for item in leaked_package.violations)

    leaked_root = engine.evaluate(
        _snapshot(
            [
                GiteaFileChange(filename="apps/app-one/src/index.ts", additions=4, deletions=0),
                GiteaFileChange(filename="README.md", additions=1, deletions=0),
            ]
        )
    )
    assert any(item.rule == "workspace_isolation" for item in leaked_root.violations)

    clean = engine.evaluate(
        _snapshot(
            [
                GiteaFileChange(filename="apps/app-one/src/index.ts", additions=4, deletions=0),
                GiteaFileChange(filename="apps/app-one/src/util.ts", additions=1, deletions=0),
            ]
        )
    )
    assert all(item.rule != "workspace_isolation" for item in clean.violations)


def test_path_rules_loaded() -> None:
    loaded = load_review_rules(Path(__file__).resolve().parents[3] / "config")
    assert "auth/**" in loaded.global_rules.path_rules
    assert loaded.global_rules.ai_review.minimum_confidence == 0.75
    assert loaded.global_rules.automation.mode == "review_only"
    assert "post_review" in loaded.global_rules.automation.allowed_actions
    assert "merge_pr" in loaded.global_rules.automation.forbidden_actions
