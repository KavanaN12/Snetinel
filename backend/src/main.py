"""
Sentinel backend entrypoint.

The auth router is already wired, and the workspace router is added here in
line with the existing thin composition-root pattern.
"""
from fastapi import FastAPI

from src.modules.ai_explanation.controllers.ai_explanation_controller import router as ai_explanation_router
from src.modules.attack_path.controllers.attack_path_controller import router as attack_path_router
from src.modules.audit.controllers.audit_controller import router as audit_router
from src.modules.audit.middleware import audit_middleware
from src.modules.auth.controllers.auth_controller import router as auth_router
from src.modules.compliance.controllers.compliance_controller import router as compliance_router
from src.modules.dashboard.controllers.dashboard_controller import router as dashboard_router
from src.modules.discovery.controllers.discovery_controller import router as discovery_router
from src.modules.drift.controllers.drift_controller import router as drift_router
from src.modules.graph.controllers.graph_controller import router as graph_router
from src.modules.rag.controllers.rag_controller import router as rag_router
from src.modules.risk_scoring.controllers.risk_scoring_controller import router as risk_scoring_router
from src.modules.workspace.controllers.workspace_controller import router as workspace_router
from src.shared.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.middleware("http")(audit_middleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(attack_path_router, prefix="/api/v1")
app.include_router(risk_scoring_router, prefix="/api/v1")
app.include_router(ai_explanation_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(compliance_router, prefix="/api/v1")
app.include_router(drift_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/readyz", tags=["health"])
async def readiness_check() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/livez", tags=["health"])
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}
