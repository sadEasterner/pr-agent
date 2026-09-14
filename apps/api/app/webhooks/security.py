from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request, status

from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)


def _compare(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))


def verify_webhook_signature(
    payload: bytes,
    secret: str,
    signature_header: str | None,
) -> bool:
    if not secret:
        return False
    if not signature_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    if _compare(expected, signature_header):
        return True
    if _compare(digest, signature_header):
        return True
    sha1 = hmac.new(secret.encode("utf-8"), payload, hashlib.sha1).hexdigest()
    if _compare(f"sha1={sha1}", signature_header) or _compare(sha1, signature_header):
        return True
    return False


async def require_gitea_signature(request: Request, settings: Settings) -> bytes:
    body = await request.body()
    if len(body) > settings.max_request_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload exceeds size limit",
        )
    provided = (
        request.headers.get("x-gitea-signature")
        or request.headers.get("x-hub-signature-256")
        or request.headers.get("x-hub-signature")
    )
    if not verify_webhook_signature(body, settings.gitea_webhook_secret, provided):
        logger.warning("webhook_signature_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    return body
