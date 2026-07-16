"""
Auth controller — the ONLY layer in this module allowed to know about
FastAPI/HTTP. Responsible for: request validation (via Pydantic schemas,
handled automatically), DI wiring of the service, and translating domain
exceptions raised by AuthService into HTTP responses.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.domain.exceptions import (
    InvalidCredentialsError,
    TokenNotFoundError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from src.modules.auth.repositories.postgres_refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from src.modules.auth.repositories.postgres_user_repository import PostgresUserRepository
from src.modules.auth.schemas.requests import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest
from src.modules.auth.schemas.responses import TokenResponse, UserResponse
from src.modules.auth.services.auth_service import AuthService
from src.shared.db.session import get_db_session
from src.shared.security.rate_limiter import InMemoryRateLimiter, get_login_rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    """
    DI wiring point. This is the ONLY place that decides which concrete
    repository implementations back the service — swapping
    PostgresRefreshTokenRepository for a future RedisRefreshTokenRepository
    (Phase 4, per ADR-002) means changing this one function, not
    auth_service.py or auth_controller.py's business logic.
    """
    user_repo = PostgresUserRepository(session)
    refresh_token_repo = PostgresRefreshTokenRepository(session)
    return AuthService(user_repository=user_repo, refresh_token_repository=refresh_token_repo)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        user = await auth_service.register(email=payload.email, password=payload.password)
        await session.commit()
        return UserResponse.model_validate(user, from_attributes=True)
    except UserAlreadyExistsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    limiter: InMemoryRateLimiter = Depends(get_login_rate_limiter),
) -> TokenResponse:
    # Rate-limit key combines email + client IP: prevents both a single
    # attacker hammering one account and a single IP spraying many accounts.
    rate_limit_key = f"login:{payload.email}:{request.client.host if request.client else 'unknown'}"
    if not limiter.check_and_increment(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    try:
        token_pair = await auth_service.login(email=payload.email, password=payload.password)
        await session.commit()
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
        )
    except InvalidCredentialsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        token_pair = await auth_service.refresh(payload.refresh_token)
        await session.commit()
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
        )
    except (TokenNotFoundError, TokenRevokedError) as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    # Idempotent by design in the service layer — always succeeds, per
    # AuthService.logout() docstring, so no exception handling needed here.
    await auth_service.logout(payload.refresh_token)
    await session.commit()
