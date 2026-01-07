import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AddressCreate, AddressUpdate
from app.repositories.address import AddressRepo
from app.services.address import AddressService
from tests.utils.address import create_random_address
from tests.utils.user import create_random_user


@pytest.mark.asyncio
async def test_create_address(db: AsyncSession):
    repo = AddressRepo(db)
    service = AddressService(repo)
    user = await create_random_user(db)
    await db.commit()

    address_in = AddressCreate(street_address="123 Test", city="Nairobi", county="Nairobi")
    address = await service.create_address(owner_id=user.id, address_in=address_in)
    assert address.street_address == "123 Test"
    assert address.owner_id == user.id


@pytest.mark.asyncio
async def test_get_address(db: AsyncSession):
    repo = AddressRepo(db)
    service = AddressService(repo)
    user = await create_random_user(db)
    address = await create_random_address(db, owner_id=user.id)
    await db.commit()

    fetched = await service.get_address(address.id, user.id)
    assert fetched.id == address.id

    # Should raise for wrong owner
    with pytest.raises(HTTPException):
        await service.get_address(address.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_update_address_and_default(db: AsyncSession):
    repo = AddressRepo(db)
    service = AddressService(repo)
    user = await create_random_user(db)
    address = await create_random_address(db, owner_id=user.id)
    await db.commit()

    update_in = AddressUpdate(street_address="New St", is_default=True)
    updated = await service.update_address(address.id, user.id, update_in)
    assert updated.street_address == "New St"
    assert updated.is_default is True


@pytest.mark.asyncio
async def test_delete_address(db: AsyncSession):
    repo = AddressRepo(db)
    service = AddressService(repo)
    user = await create_random_user(db)
    address = await create_random_address(db, owner_id=user.id)
    await db.commit()

    await service.delete_address(address.id, user.id)

    # Should raise when trying to get deleted address
    with pytest.raises(HTTPException):
        await service.get_address(address.id, user.id)
