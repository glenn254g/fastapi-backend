import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import UserCreate, UserUpdate
from app.repositories.user import UserRepo
from app.services.users import UserService
from tests.utils.user import create_random_user
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.asyncio
async def test_create_user_and_duplicate(db: AsyncSession):
    repo = UserRepo(db)
    service = UserService(repo)

    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    user = await service.create_user(user_in)
    assert user.email == email

    # Duplicate should raise HTTPException
    with pytest.raises(HTTPException):
        await service.create_user(user_in)


@pytest.mark.asyncio
async def test_get_user_by_email_and_id(db: AsyncSession):
    repo = UserRepo(db)
    service = UserService(repo)
    user = await create_random_user(db)
    await db.commit()

    fetched_email = await service.get_user_by_email(user.email)
    assert fetched_email.email == user.email

    fetched_id = await service.get_user_by_id(user.id)
    assert fetched_id.id == user.id


@pytest.mark.asyncio
async def test_update_user(db: AsyncSession):
    repo = UserRepo(db)
    service = UserService(repo)
    user = await create_random_user(db)
    await db.commit()

    user_update = UserUpdate(full_name="Updated Name")
    updated = await service.update_user(user.id, user_update)
    assert updated.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_change_password(db: AsyncSession):
    repo = UserRepo(db)
    service = UserService(repo)

    # Create a user with a known password
    user = await repo.create_user(
        user_in=UserCreate(
            email="test@example.com",
            password="password123",
            full_name="Test User",
        )
    )

    old_password = "password123"
    new_password = "newpass123"

    # Change password successfully
    await service.change_password(user, old_password, new_password)

    # Wrong old password should raise
    with pytest.raises(HTTPException):
        await service.change_password(user, "wrong", "anotherpass")

    # Same password should raise
    with pytest.raises(HTTPException):
        await service.change_password(user, new_password, new_password)


@pytest.mark.asyncio
async def test_delete_user(db: AsyncSession):
    repo = UserRepo(db)
    service = UserService(repo)
    admin_user = await create_random_user(db)
    normal_user = await create_random_user(db)
    await db.commit()

    # Delete normal user
    await service.delete_user(normal_user.id, admin_user.id)

    # Deleting self should raise
    with pytest.raises(HTTPException):
        await service.delete_user(admin_user.id, admin_user.id)
