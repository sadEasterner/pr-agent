from app.ai.diff import prepare_diff_bundle, should_exclude
from app.config import Settings
from app.gitea.models import GiteaFileChange


def test_excludes_binaries_vendor_and_lockfiles() -> None:
    assert should_exclude("static/logo.png")
    assert should_exclude("frontend/node_modules/pkg/index.js")
    assert should_exclude("vendor/lib.go")
    assert should_exclude("pnpm-lock.yaml")
    assert should_exclude("dist/bundle.min.js")
    assert not should_exclude("apps/api/app/main.py")


def test_chunk_and_limit_diffs(settings: Settings) -> None:
    files = [
        GiteaFileChange(
            filename="app/main.py",
            additions=10,
            deletions=0,
            patch="+" + ("a" * 50_000),
        ),
        GiteaFileChange(
            filename="pnpm-lock.yaml",
            additions=1000,
            deletions=0,
            patch="+lock",
        ),
        GiteaFileChange(
            filename="photo.png",
            additions=0,
            deletions=0,
            patch=None,
        ),
    ]
    settings.ai_max_diff_chars = 1000
    settings.ai_chunk_size = 200
    bundle = prepare_diff_bundle(files, "", settings)
    assert "pnpm-lock.yaml" in bundle.excluded
    assert "photo.png" in bundle.excluded
    assert bundle.truncated is True
    assert bundle.chunks
