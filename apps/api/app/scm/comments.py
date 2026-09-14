from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.logging import get_logger

logger = get_logger(__name__)

REVIEW_MARKER = "PR-MANAGER-REVIEW"

ListComments = Callable[[str, int], Awaitable[list[Any]]]
CreateComment = Callable[[str, int, str], Awaitable[Any]]
UpdateComment = Callable[[str, int, int, str], Awaitable[Any]]


def _comment_body(comment: Any) -> str:
    if isinstance(comment, dict):
        return str(comment.get("body") or "")
    return str(getattr(comment, "body", "") or "")


def _comment_id(comment: Any) -> int:
    if isinstance(comment, dict):
        return int(comment["id"])
    return int(comment.id)


async def upsert_review_comment(
    *,
    provider: str,
    repository: str,
    number: int,
    body: str,
    list_comments: ListComments,
    create_comment: CreateComment,
    update_comment: UpdateComment,
) -> None:
    marked_body = f"{REVIEW_MARKER}\n{body}"
    comments = await list_comments(repository, number)
    existing = next((comment for comment in comments if REVIEW_MARKER in _comment_body(comment)), None)
    if existing is not None:
        comment_id = _comment_id(existing)
        await update_comment(repository, number, comment_id, marked_body)
        logger.info(
            "scm_comment_updated",
            provider=provider,
            repository=repository,
            pr_number=number,
            comment_id=comment_id,
        )
        return
    await create_comment(repository, number, marked_body)
    logger.info("scm_comment_created", provider=provider, repository=repository, pr_number=number)
