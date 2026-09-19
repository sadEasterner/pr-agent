from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.deps import require_admin
from app.api.health import router as health_router
from app.api.prs import router as prs_router
from app.api.reviews import router as reviews_router
from app.api.settings import router as settings_router
from app.config import get_settings
from app.db.session import SessionLocal, engine
from app.exports.router import router as exports_router
from app.jobs.processor import ReviewProcessor
from app.jobs.queue import JobQueue
from app.logging import configure_logging, get_logger
from app.rules.loader import load_review_rules
from app.scm.factory import create_scm_provider
from app.webhooks import router as webhook_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    loaded_rules = load_review_rules(settings.config_dir)
    scm = create_scm_provider(settings)
    processor = ReviewProcessor(settings, SessionLocal, loaded_rules, scm)
    queue = JobQueue(processor.process)
    app.state.settings = settings
    app.state.job_queue = queue
    app.state.processor = processor
    app.state.scm = scm
    await queue.start()
    logger.info("application_started", env=settings.app_env, scm_provider=settings.git_provider)
    try:
        yield
    finally:
        await queue.stop()
        await scm.close()
        await engine.dispose()


def create_app(*, start_workers: bool = True) -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Gitea PR Manager",
        description="Internal PR management and AI code-review platform. AI is advisory only.",
        version="1.0.0",
        lifespan=lifespan if start_workers else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.settings = settings
    application.include_router(health_router)
    application.include_router(webhook_router)
    application.include_router(auth_router)
    application.include_router(admin_router)
    application.include_router(prs_router)
    application.include_router(reviews_router)
    application.include_router(analytics_router)
    application.include_router(exports_router)
    application.include_router(settings_router)
    application.middleware("http")(require_admin)

    @application.middleware("http")
    async def limit_request_size(request: Request, call_next):  # type: ignore[no-untyped-def]
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_bytes:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)

    return application


app = create_app()
