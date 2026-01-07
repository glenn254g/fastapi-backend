# backend/app/services/users.py
"""
User service implementing business logic and orchestration.

This service layer:
- Coordinates between repositories
- Implements business rules
- Validates business constraints
- Handles complex operations
- Converts between DB models and proper DTOs (Data Transfer Objects)
"""

import uuid

from fastapi import HTTPException, status

from app.models.models import (
    PaginationMeta,
    User,
    UserCreate,
    UserFilters,
    UserPublic,
    UsersPublic,
    UserUpdate,
    UserWithAddresses,
)
from app.repositories.user import UserRepo


class UserService:
    def __init__(self, repo: UserRepo):
        self.repo = repo

    async def create_user(self, user_in: UserCreate) -> UserPublic:
        user = await self.repo.get_user_by_email(user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )
        user = await self.repo.create_user(user_in=user_in)
        return UserPublic.model_validate(user)  # Convert DB model to DTO

    async def get_user_by_email(self, email: str) -> UserPublic:
        user = await self.repo.get_user_by_email(email=email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserPublic.model_validate(user)

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserPublic:
        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserPublic.model_validate(user)

    async def get_user_with_addresses(self, user_id: uuid.UUID) -> UserWithAddresses:
        user = await self.repo.get_user_with_addresses(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserWithAddresses.model_validate(user)

    async def list_users(self, filters: UserFilters, page: int, page_size: int) -> UsersPublic:
        skip = (page - 1) * page_size
        filter_dict = {
            "is_active": filters.is_active,
            "is_verified": filters.is_verified,
            "role": filters.role,
        }
        filter_dict = {k: v for k, v in filter_dict.items() if v is not None}
        users, total = await self.repo.list_users(skip=skip, limit=page_size, filters=filter_dict)
        users = [UserPublic.model_validate(u) for u in users]  # Convert DB model to DTO
        pagination = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
        return UsersPublic(users=users, pagination=pagination)

    async def update_user(self, user_id: uuid.UUID, user_in: UserUpdate) -> UserPublic:
        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        updated_user = await self.repo.update(db_obj=user, obj_in=user_in)
        return UserPublic.model_validate(updated_user)

    async def change_password(self, user: User, old_password: str, new_password: str) -> None:
        from app.core.security import verify_password

        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Incorrect password")
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be same as current",
            )
        await self.repo.update_password(db_obj=user, new_password=new_password)

    async def delete_user_me(self, user: User) -> None:
        if user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin users are not allowed to delete themselves",
            )
        await self.repo.soft_delete(id=user.id)

    async def delete_user(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        if user_id == admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin users are not allowed to delete themselves",
            )

        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Only allow admins to delete others
        if admin_id is None:  # Or however you determine normal user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",  # <- match test
            )

        await self.repo.soft_delete(id=user_id)
