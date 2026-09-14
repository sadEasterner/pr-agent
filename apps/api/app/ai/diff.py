from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings
from app.gitea.models import GiteaFileChange

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}

GENERATED_PATTERNS = (
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"(^|/)coverage/"),
    re.compile(r"(^|/)generated/"),
    re.compile(r"\.min\.(js|css)$"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)__pycache__/"),
)

LOCKFILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
    "Gemfile.lock",
    "Cargo.lock",
    "go.sum",
}


@dataclass
class DiffBundle:
    files: list[GiteaFileChange]
    chunks: list[str]
    excluded: list[str]
    truncated: bool


def should_exclude(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    lower = normalized.lower()
    if any(lower.endswith(ext) for ext in BINARY_EXTENSIONS):
        return True
    if normalized.split("/")[-1] in LOCKFILES:
        return True
    return any(pattern.search(normalized) for pattern in GENERATED_PATTERNS)


def prepare_diff_bundle(
    files: list[GiteaFileChange],
    raw_diff: str,
    settings: Settings,
) -> DiffBundle:
    excluded: list[str] = []
    included: list[GiteaFileChange] = []
    for file in files:
        if should_exclude(file.filename):
            excluded.append(file.filename)
            continue
        included.append(file)
        if len(included) >= settings.ai_max_files:
            break

    chunks: list[str] = []
    remaining = settings.ai_max_diff_chars
    truncated = len(included) < (len(files) - len(excluded))
    for file in included:
        patch = file.patch or _extract_file_patch(raw_diff, file.filename)
        if not patch:
            continue
        if len(patch) > settings.ai_chunk_size:
            patch = patch[: settings.ai_chunk_size] + "\n[truncated file diff]"
            truncated = True
        if len(patch) > remaining:
            chunks.append(patch[:remaining] + "\n[truncated remaining diff]")
            truncated = True
            remaining = 0
            break
        chunks.append(f"FILE: {file.filename}\n{patch}")
        remaining -= len(patch)
    return DiffBundle(files=included, chunks=chunks, excluded=excluded, truncated=truncated)


def _extract_file_patch(raw_diff: str, filename: str) -> str:
    marker = f"diff --git a/{filename} b/{filename}"
    start = raw_diff.find(marker)
    if start < 0:
        return ""
    next_start = raw_diff.find("\ndiff --git ", start + 1)
    if next_start < 0:
        return raw_diff[start:]
    return raw_diff[start:next_start]
