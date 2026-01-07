# backend/app/repositories/base.py
"""
Base repository implementing the Repository Pattern.

This module provides a generic base repository class that handles common CRUD
operations with:
- Automatic soft-delete filtering
- Type-safe operations using Python generics

Example:
    >>> class UserRepo(BaseRepo[User, UserCreate, UserUpdate]):
    >>>     def __init__(self, session: AsyncSession):
    >>>         super().__init__(model=User, session=session)
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class BaseRepo(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    `Generic base repository` for database operations.

    Type Parameters:

        ModelType: SQLModel database model class
        CreateSchemaType: Pydantic schema for creation
        UpdateSchemaType: Pydantic schema for updates

    Attributes:
        model: The ``database`` model class this repository manages
        session: Async database session for executing queries

    For example::

        >>> repo = UserRepo(session)
        >>> user = await repo.get(user_id)
        >>> users = await repo.get_listing(skip=0, limit=10)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _base_query(self):
        """
        Build base query with automatic soft-delete filtering.

        Automatically excludes soft-deleted records (where deleted_at IS NOT NULL)
        if the model supports soft deletes.

        Returns:
            Select: SQLAlchemy select statement with base filters applied
        """
        query = select(self.model)
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def get(self, id: UUID) -> ModelType | None:
        """
        Retrieve a single record by primary key.
        Automatically filters out soft-deleted records.

        Args:
            id: UUID primary key of the record

        Example:

            ```python
            user = await repo.get(user_id)
            if user:
                print(f"Found: {user.email}")
            ```
        """
        query = self._base_query().where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_listing(
        self, *, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> Sequence[ModelType]:
        """
        Retrieve a paginated list of records with optional filtering.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Dictionary of field-value pairs for filtering

        Returns:
            Sequence[ModelType]: List of model instances matching criteria

        Example:
            >>> users = await repo.get_listing(
            >>>     skip=0,
            >>>     limit=20,
            >>>     filters={"is_active": True, "role": "customer"}
            >>> )
        """
        query = self._base_query()
        # Apply filters
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_count(self, *, filters: dict[str, Any] | None = None) -> int:
        """
        Count records matching optional filters.

        Useful for pagination metadata (total pages, etc.).

        Args:
            filters: Dictionary of field-value pairs for filtering

        Returns:
            int: Number of records matching criteria

        Example:
            >>> total = await repo.get_count(filters={"is_active": True})
            >>> total_pages = (total + page_size - 1) // page_size
        """
        query = select(func.count()).select_from(self.model)
        # Apply soft delete filter
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record in the database.

        Args:
            obj_in: Pydantic schema containing creation data

        Returns:
            ModelType: Newly created model instance with ID

        Raises:
            DatabaseError: If creation fails

        Example:
            >>> user_data = UserCreate(email="user@example.com", password="secret")
            >>> user = await repo.create(obj_in=user_data)
        """
        db_obj = self.model(**obj_in.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """
        Update an existing record with new values.

        Only updates fields that are explicitly set in obj_in.
        Automatically updates the 'updated_at' timestamp if present.

        Args:
            db_obj: Existing model instance to update
            obj_in: Pydantic schema or dict with update data

        Returns:
            ModelType: Updated model instance

        Raises:
            SoftDeletedError: If attempting to update a deleted record

        Example:
            >>> user = await repo.get(user_id)
            >>> update_data = UserUpdate(full_name="John Doe")
            >>> updated_user = await repo.update(db_obj=user, obj_in=update_data)
        """
        if hasattr(db_obj, "deleted_at") and db_obj.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found or has been deleted")
        # Get update data
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        # Apply updates to model
        updated_fields = []
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            updated_fields.append(field)

        # Update timestamp if exists
        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.utcnow()
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, *, id: UUID) -> bool:
        """
        Permanently delete a record from the database (hard delete).

        ⚠️ WARNING: This permanently removes data. Consider using soft_delete instead.

        Args:
            id: UUID of record to delete

        Returns:
            bool: True if deleted, False if not found

        Example:
            >>> success = await repo.delete(id=user_id)
        """
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False

    async def soft_delete(self, *, id: UUID) -> ModelType:
        """
        Soft delete a record by setting deleted_at timestamp.

        Soft-deleted records are automatically excluded from queries but remain
        in the database for audit trails and potential recovery.

        Args:
            db_obj: Model instance to soft delete

        Returns:
            ModelType: Soft-deleted model instance

        Raises:
            ValueError: If model doesn't support soft deletes

        Example:
            >>> user = await repo.get(user_id)
            >>> await repo.soft_delete(db_obj=user)
        """
        if not hasattr(self.model, "deleted_at"):
            raise ValueError(
                f"{self.model.__name__} does not support soft delete. "
                "Add 'deleted_at: datetime | None' field to enable."
            )
        db_obj = await self.get(id)
        if not db_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{self.model.__name__} not found")

        db_obj.deleted_at = datetime.utcnow()
        self.session.add(db_obj)
        await self.session.commit()
        return db_obj
