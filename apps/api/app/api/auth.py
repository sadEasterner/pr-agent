from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import (
    clear_session_cookie,
    credentials_match,
    issue_session,
    session_username,
    set_session_cookie,
)
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AuthOut(BaseModel):
    authenticated: bool
    username: str | None = None


@router.post("/login", response_model=AuthOut)
async def login(payload: LoginIn, response: Response, settings: Settings = Depends(get_settings)) -> AuthOut:
    if not credentials_match(payload.username, payload.password, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    set_session_cookie(response, issue_session(settings.admin_username, settings), settings)
    return AuthOut(authenticated=True, username=settings.admin_username)


@router.post("/logout", response_model=AuthOut)
async def logout(response: Response, settings: Settings = Depends(get_settings)) -> AuthOut:
    clear_session_cookie(response, settings)
    return AuthOut(authenticated=False, username=None)


@router.get("/me", response_model=AuthOut)
async def me(request: Request, settings: Settings = Depends(get_settings)) -> AuthOut:
    username = session_username(request, settings)
    if not username:
        return AuthOut(authenticated=False, username=None)
    return AuthOut(authenticated=True, username=username)
