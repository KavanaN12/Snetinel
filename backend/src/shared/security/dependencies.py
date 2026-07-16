"""
Authentication dependency shared across all modules.

This is the ONLY entry point other modules (workspace, cloud_discovery, etc.)
should depend on to authenticate a request. It deliberately lives in
`shared/security`, not `modules/auth`, so that downstream modules depend on
a stable, minimal contract (a verified user_id) rather than importing auth's
internal services/repositories — preserving the dependency direction defined
in the SAD's module dependency diagram.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db.session import get_db_session
from src.shared.security.jwt_handler import JWTHandler, TokenExpiredError, TokenInvalidError

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    Decodes and validates the access token, returning the authenticated
    user_id. Does NOT hit the database — token validity alone is sufficient
    to authenticate; existence/activity checks on the user happen wherever
    a downstream service actually needs the full user record.
    """
    token = credentials.credentials
    try:
        return JWTHandler.decode_access_token(token)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# Re-exported so downstream modules can type-hint a DB session without
# importing shared.db directly in every controller.
DbSession = AsyncSession
GetDbSession = Depends(get_db_session)
