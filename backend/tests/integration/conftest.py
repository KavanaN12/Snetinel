"""
Integration test fixtures.

These tests exercise the full stack: FastAPI routing -> Pydantic validation
-> AuthService -> Postgres repositories -> a real database. They require a
running Postgres instance (see docker-compose.yml / README "Running Tests").

Unlike the unit tests (tests/unit/auth), these are NOT expected to run
without infrastructure — that split is intentional and matches the SAD's
distinction between unit and integration test suites.
"""
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.main import app
from src.shared.db.session import Base, get_db_session

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_test",
)


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
