from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth import is_public_path, session_username
from app.config import Settings


async def require_admin(request: Request, call_next):  # type: ignore[no-untyped-def]
    settings: Settings = request.app.state.settings if hasattr(request.app.state, "settings") else None
    if settings is None:
        from app.config import get_settings

        settings = get_settings()
    if is_public_path(request.url.path, request.method, settings):
        return await call_next(request)
    username = session_username(request, settings)
    if not username:
        return JSONResponse({"detail": "Not authenticated"}, status_code=status.HTTP_401_UNAUTHORIZED)
    request.state.admin_user = username
    return await call_next(request)


def require_admin_user(request: Request) -> str:
    username = getattr(request.state, "admin_user", None)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return username
