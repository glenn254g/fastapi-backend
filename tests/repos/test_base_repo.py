# backend/tests/repositories/test_base_repo.py
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from app.repositories.base import BaseRepo


# -------------------------
# Dummy Model for testing
# -------------------------
class DummyModel(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    value: int
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


# -------------------------
# Fixture: Repo instance
# -------------------------
@pytest.fixture
def repo(db: AsyncSession):
    return BaseRepo(DummyModel, db)


# -------------------------
# Test CRUD operations
# -------------------------
@pytest.mark.asyncio
async def test_create_get(repo: BaseRepo, db: AsyncSession):
    obj_in: dict[str, Any] = {"name": "foo", "value": 123}
    db_obj = await repo.create(obj_in=DummyModel(**obj_in))
    assert db_obj.id
    assert db_obj.name == "foo"

    fetched = await repo.get(db_obj.id)
    assert fetched.id == db_obj.id
    assert fetched.name == "foo"


@pytest.mark.asyncio
async def test_update(repo: BaseRepo, db: AsyncSession):
    db_obj = await repo.create(obj_in=DummyModel(name="foo", value=1))
    updated_obj = await repo.update(db_obj=db_obj, obj_in=DummyModel(name="bar", value=2))
    assert updated_obj.name == "bar"
    assert updated_obj.value == 2
    assert updated_obj.updated_at is not None


@pytest.mark.asyncio
async def test_delete(repo: BaseRepo, db: AsyncSession):
    db_obj = await repo.create(obj_in=DummyModel(name="foo", value=1))
    result = await repo.delete(id=db_obj.id)
    assert result is True
    assert await repo.get(db_obj.id) is None


@pytest.mark.asyncio
async def test_soft_delete(repo: BaseRepo, db: AsyncSession):
    db_obj = await repo.create(obj_in=DummyModel(name="foo", value=1))
    soft_deleted = await repo.soft_delete(id=db_obj.id)
    assert soft_deleted.deleted_at is not None

    # Trying to soft delete again raises
    with pytest.raises(HTTPException):
        await repo.soft_delete(id=str(uuid4()))


@pytest.mark.asyncio
async def test_get_listing_filters(repo: BaseRepo, db: AsyncSession):
    # create multiple entries
    await repo.create(obj_in=DummyModel(name="a", value=1))
    await repo.create(obj_in=DummyModel(name="b", value=2))
    await repo.create(obj_in=DummyModel(name="c", value=1))

    results = await repo.get_listing(filters={"value": 1})
    assert len(results) == 2
    assert all(r.value == 1 for r in results)


@pytest.mark.asyncio
async def test_get_count(repo: BaseRepo, db: AsyncSession):
    await repo.create(obj_in=DummyModel(name="a", value=1))
    await repo.create(obj_in=DummyModel(name="b", value=2))
    count = await repo.get_count()
    assert count >= 2

    count_filtered = await repo.get_count(filters={"value": 1})
    assert count_filtered >= 1
