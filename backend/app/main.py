from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local-first AI document intelligence app foundation.",
    )

    app.include_router(health_router)

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

