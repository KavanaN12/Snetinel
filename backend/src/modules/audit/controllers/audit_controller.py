from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from src.modules.audit.repositories.postgres_audit_log_repository import PostgresAuditLogRepository
from src.modules.audit.schemas.responses import AuditLogResponse
from src.modules.audit.services.audit_service import AuditService
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/audit", tags=["audit"])


def get_audit_service(session=Depends(get_db_session)) -> AuditService:
    return AuditService(audit_log_repository=PostgresAuditLogRepository(session))


@router.get("/logs", response_model=list[AuditLogResponse])
async def list_logs(
    current_user_id: str = Depends(get_current_user_id),
    service: AuditService = Depends(get_audit_service),
) -> list[AuditLogResponse]:
    logs = await service.list_for_actor(current_user_id)
    return [AuditLogResponse(**asdict(log)) for log in logs]
