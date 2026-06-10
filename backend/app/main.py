from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.api.routes_projects import router as projects_router
from backend.app.core.config import get_settings
from backend.app.core.database import init_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_database()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local-first AI document intelligence app foundation.",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(projects_router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "ready",
            "mode": "local-first",
        }

    return app


app = create_app()
