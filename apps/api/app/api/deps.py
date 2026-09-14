from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth import is_public_path, session_username
from app.config import Settings, get_settings


async def require_admin(request: Request, call_next):  # type: ignore[no-untyped-def]
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if settings is None:
        settings = get_settings()
    if is_public_path(request.url.path, request.method, settings):
        return await call_next(request)
    username = session_username(request, settings)
    if not username:
        return JSONResponse({"detail": "Not authenticated"}, status_code=status.HTTP_401_UNAUTHORIZED)
    request.state.admin_user = username
    return await call_next(request)


def require_admin_user(request: Request, settings: Settings = Depends(get_settings)) -> str:
    username = getattr(request.state, "admin_user", None) or session_username(request, settings)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return username
