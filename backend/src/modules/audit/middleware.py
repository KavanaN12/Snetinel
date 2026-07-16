from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Request
from starlette.responses import Response

from src.modules.audit.repositories.postgres_audit_log_repository import PostgresAuditLogRepository
from src.modules.audit.services.audit_service import AuditService
from src.shared.db.session import AsyncSessionLocal, get_db_session
from src.shared.security.jwt_handler import JWTHandler, TokenExpiredError, TokenInvalidError


async def audit_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    actor_id: str | None = None
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            actor_id = JWTHandler.decode_access_token(token)
        except (TokenExpiredError, TokenInvalidError):
            actor_id = None

    response = await call_next(request)

    if actor_id:
        session = None
        session_generator = None
        try:
            override = request.app.dependency_overrides.get(get_db_session)
            if override is not None:
                session_generator = override()
                session = await anext(session_generator)
            else:
                async with AsyncSessionLocal() as fallback_session:
                    audit_service = AuditService(audit_log_repository=PostgresAuditLogRepository(fallback_session))
                    await audit_service.log_event(
                        actor_id=actor_id,
                        action="request",
                        resource=request.url.path,
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                    )
                    await fallback_session.commit()
                return response

            audit_service = AuditService(audit_log_repository=PostgresAuditLogRepository(session))
            await audit_service.log_event(
                actor_id=actor_id,
                action="request",
                resource=request.url.path,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )
            await session.commit()
        except Exception:
            if session is not None:
                await session.rollback()
        finally:
            if session_generator is not None:
                await session_generator.aclose()

    return response
