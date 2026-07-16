"""
Sentinel backend entrypoint.

The auth router is already wired, and the workspace router is added here in
line with the existing thin composition-root pattern.
"""
from fastapi import FastAPI

from src.modules.auth.controllers.auth_controller import router as auth_router
from src.modules.discovery.controllers.discovery_controller import router as discovery_router
from src.modules.workspace.controllers.workspace_controller import router as workspace_router
from src.shared.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
