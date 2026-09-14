from __future__ import annotations

import hashlib
import hmac
import time
from typing import Final

from fastapi import Request, Response

from app.config import Settings

COOKIE_NAME: Final = "pr_manager_session"


def _hashed(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def credentials_match(given_username: str, given_password: str, settings: Settings) -> bool:
    if not settings.admin_username or not settings.admin_password:
        return False
    user_ok = hmac.compare_digest(_hashed(given_username), _hashed(settings.admin_username))
    password_ok = hmac.compare_digest(_hashed(given_password), _hashed(settings.admin_password))
    return user_ok and password_ok


def issue_session(username: str, settings: Settings) -> str:
    expires = int(time.time()) + settings.auth_session_seconds
    payload = f"{username}:{expires}"
    signature = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def read_session(token: str | None, settings: Settings) -> str | None:
    if not token or not settings.auth_session_secret or not settings.admin_username:
        return None
    parts = token.split(":")
    if len(parts) != 3:
        return None
    username, expires_raw, signature = parts
    payload = f"{username}:{expires_raw}"
    expected = hmac.new(
        settings.auth_session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        expires = int(expires_raw)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    if not hmac.compare_digest(_hashed(username), _hashed(settings.admin_username)):
        return None
    return username


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.auth_session_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.auth_cookie_secure, samesite="lax")


def session_username(request: Request, settings: Settings) -> str | None:
    return read_session(request.cookies.get(COOKIE_NAME), settings)


def is_public_path(path: str, method: str, settings: Settings) -> bool:
    if method == "OPTIONS":
        return True
    public = {
        "/health",
        "/ready",
        "/webhooks/gitea",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
    }
    if path in public:
        return True
    if not settings.is_production and path in {"/docs", "/redoc", "/openapi.json"}:
        return True
    return False
