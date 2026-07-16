"""
Database session management (async SQLAlchemy).

This is infrastructure — the only layer allowed to know about engines,
connection pools, and sessions. Repositories receive a session via
dependency injection; they never construct one themselves outside of this
module, which keeps repositories trivially testable against an in-memory
or test database.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.shared.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base — every module's ORM model inherits from this."""


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a scoped session per request.
    Commits are the responsibility of the service layer (explicit, not
    implicit on every request) — this dependency only guarantees the
    session is closed, and rolls back on unhandled exceptions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
