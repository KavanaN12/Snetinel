from __future__ import annotations

from fastapi import APIRouter, Depends

from src.modules.drift.repositories.postgres_drift_event_repository import PostgresDriftEventRepository
from src.modules.drift.schemas.responses import DriftEventResponse
from src.modules.drift.services.drift_detection_service import DriftDetectionService
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/drift", tags=["drift"])


def get_drift_service(session=Depends(get_db_session)) -> DriftDetectionService:
    return DriftDetectionService(drift_event_repository=PostgresDriftEventRepository(session))


@router.get("/workspaces/{workspace_id}/events", response_model=list[DriftEventResponse])
async def list_events(
    workspace_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: DriftDetectionService = Depends(get_drift_service),
) -> list[DriftEventResponse]:
    del current_user_id
    events = await service._drift_event_repository.list_for_workspace(workspace_id)  # type: ignore[attr-defined]
    return [DriftEventResponse(**event.__dict__) for event in events]
