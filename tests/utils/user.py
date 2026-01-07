"""
User-related test utilities.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import User, UserCreate
from app.repositories.user import UserRepo
from tests.utils.utils import (
    random_email,
    random_lower_string,
    random_phone_number,
)


async def create_random_user(db: AsyncSession, **kwargs) -> User:
    """Create a random user for testing."""
    repo = UserRepo(db)

    user_in = UserCreate(
        email=kwargs.get("email", random_email()),
        password=kwargs.get("password", random_lower_string()),
        full_name=kwargs.get("full_name", f"Test {random_lower_string(8)}"),
        phone_number=kwargs.get("phone_number", random_phone_number()),
        role=kwargs.get("role", "customer"),
        is_active=kwargs.get("is_active", True),
        is_verified=kwargs.get("is_verified", False),
    )

    user = await repo.create_user(user_in=user_in)
    await db.commit()
    await db.refresh(user)
    return user


async def user_authentication_headers(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """Get authentication headers for a user."""
    data = {"username": email, "password": password}
    response = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=data)

    if response.status_code != 200:
        raise Exception(f"Login failed for {email}: {response.status_code} - {response.text}")

    tokens = response.json()
    access_token = tokens["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


async def get_admin_user_token_headers(client: AsyncClient) -> dict[str, str]:
    """Get authentication headers for the superuser."""
    return await user_authentication_headers(
        client=client,
        email=settings.ADMIN,
        password=settings.ADMIN_PASSWORD,
    )


async def authentication_token_from_email(client: AsyncClient, email: str, db: AsyncSession) -> dict[str, str]:
    """
    Return valid token for user with given email.
    If user doesn't exist, create them first.
    """
    password = "test_password_123"
    repo = UserRepo(db)

    user = await repo.get_user_by_email(email)

    if not user:
        user = await create_random_user(db, email=email, password=password)
        await db.commit()

    return await user_authentication_headers(client=client, email=email, password=password)
