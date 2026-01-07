import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.models import UserCreate
from app.repositories.user import UserRepo
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.asyncio
class TestUserRepo:
    """Test suite for UserRepo."""

    async def test_create_user(self, db: AsyncSession):
        """Should create user with hashed password."""
        repo = UserRepo(session=db)
        email = random_email()
        password = random_lower_string()
        user_in = UserCreate(email=email, password=password)
        user = await repo.create_user(user_in=user_in)
        await db.commit()
        assert user.email == email
        assert hasattr(user, "hashed_password")
        assert verify_password(password, user.hashed_password)

    async def test_get_user_by_email(self, db: AsyncSession):
        """Should retrieve user by email."""
        repo = UserRepo(session=db)
        email = random_email()
        user_in = UserCreate(email=email, password=random_lower_string())
        await repo.create_user(user_in=user_in)
        await db.commit()
        user = await repo.get_user_by_email(email)
        assert user is not None
        assert user.email == email

    async def test_get_user_by_email_not_found(self, db: AsyncSession):
        """Repository returns None for non-existent email."""
        repo = UserRepo(session=db)
        user = await repo.get_user_by_email("nonexistent@test.com")
        assert user is None

    async def test_get_user_with_addresses(self, db: AsyncSession):
        """Should eagerly load user addresses."""
        from tests.utils.address import create_random_address
        from tests.utils.user import create_random_user

        repo = UserRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        # Create address and commit
        await create_random_address(db, owner_id=user.id)
        await db.commit()

        # Now fetch user with addresses
        user_with_addresses = await repo.get_user_with_addresses(user.id)
        assert user_with_addresses is not None
        assert hasattr(user_with_addresses, "addresses")
        assert len(user_with_addresses.addresses) >= 1

    async def test_list_users_with_filters(self, db: AsyncSession):
        """Should filter users correctly."""
        repo = UserRepo(session=db)
        await repo.create_user(
            user_in=UserCreate(
                email=random_email(),
                password=random_lower_string(),
                is_active=True,
            )
        )
        await repo.create_user(
            user_in=UserCreate(
                email=random_email(),
                password=random_lower_string(),
                is_active=False,
            )
        )
        await db.commit()
        users, total = await repo.list_users(filters={"is_active": True})
        assert all(user.is_active for user in users)

    async def test_update_password(self, db: AsyncSession):
        """Should update user password."""
        repo = UserRepo(session=db)
        old_password = random_lower_string()
        user_in = UserCreate(email=random_email(), password=old_password)
        user = await repo.create_user(user_in=user_in)
        await db.commit()
        new_password = random_lower_string()
        updated = await repo.update_password(db_obj=user, new_password=new_password)
        await db.commit()
        assert verify_password(new_password, updated.hashed_password)
        assert not verify_password(old_password, updated.hashed_password)
