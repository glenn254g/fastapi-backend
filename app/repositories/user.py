# backend/app/repositories/user.py

import uuid
from datetime import datetime

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import get_password_hash
from app.models.models import (
    User,
    UserCreate,
    UserUpdate,
)
from app.repositories.base import BaseRepo


class UserRepo(BaseRepo[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=User, session=session)

    async def create_user(self, *, user_in: UserCreate) -> User:
        db_obj = User(
            **user_in.model_dump(exclude={"password"}),
            hashed_password=get_password_hash(user_in.password),
        )
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def get_user_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_with_addresses(self, user_id: uuid.UUID) -> User | None:
        """Return a User with addresses eagerly loaded (selectinload)."""
        statement = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(
                selectinload(User.addresses),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_users(
        self, *, skip: int = 0, limit: int = 100, filters: dict | None = None
    ) -> tuple[list[User], int]:
        """List users with addresses and return (users, total_count)."""
        users = await self.get_listing(skip=skip, limit=limit, filters=filters)
        total = await self.get_count(filters=filters)
        return users, int(total)

    async def update_password(self, *, db_obj: User, new_password: str) -> User:
        db_obj.hashed_password = get_password_hash(new_password)
        db_obj.updated_at = datetime.utcnow()
        self.session.add(db_obj)
        await self.session.commit()
        return db_obj
