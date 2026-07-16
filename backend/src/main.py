"""
Sentinel backend entrypoint.

Phase 2 wires only the auth module's router. Subsequent phases add their
routers here following the same pattern — this file stays a thin
composition root, never business logic.
"""
from fastapi import FastAPI

from src.modules.auth.controllers.auth_controller import router as auth_router
from src.shared.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
