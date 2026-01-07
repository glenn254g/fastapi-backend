# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.db import get_async_session
from app.main import app
from app.repositories.user import UserRepo
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_admin_token_headers

# Create test engine
test_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    future=True,
    pool_pre_ping=True,
    poolclass=None,  # Disable pooling for tests
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    from app.models.models import SQLModel

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    # Dispose engine to close all connections
    await test_engine.dispose()


# HTTP client fixture
@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing."""

    async def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_async_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Admin token fixture
@pytest_asyncio.fixture(scope="function")
async def admin_token_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    """Get admin authentication headers."""
    from app.core.db import init_db

    repo = UserRepo(session=db)
    await init_db(db, repo)
    await db.commit()

    return await get_admin_token_headers(client)


# Normal user token fixture
@pytest_asyncio.fixture(scope="function")
async def normal_user_token_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    """Get normal user authentication headers."""
    return await authentication_token_from_email(client=client, email=settings.EMAIL_TEST_USER, db=db)
