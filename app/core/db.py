# backend/app/core/db.py

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import select

from app.core.config import settings

engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,  # Set to True only for debugging
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db(session: AsyncSession, repo=None) -> None:
    from app.models.models import User, UserCreate, UserRole
    from app.repositories.user import UserRepo

    repo = UserRepo(session=session)
    q = select(User).where(User.email == settings.ADMIN)
    result = await session.execute(q)
    user = result.scalar_one_or_none()
    if not user:
        user_in = UserCreate(
            email=settings.ADMIN,
            password=settings.ADMIN_PASSWORD,
            role=UserRole.ADMIN,
        )
        user = await repo.create_user(user_in=user_in)
