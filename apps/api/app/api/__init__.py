from app.api.analytics import router as analytics_router
from app.api.health import router as health_router
from app.api.prs import router as prs_router
from app.api.settings import router as settings_router

__all__ = ["analytics_router", "health_router", "prs_router", "settings_router"]
