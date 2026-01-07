# backend/app/repositories/addresses.py

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    Address,
    AddressCreate,
    AddressUpdate,
)
from app.repositories.base import BaseRepo


class AddressRepo(BaseRepo[Address, AddressCreate, AddressUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=Address, session=session)

    async def create_address(self, *, owner_id: uuid.UUID, address_in: AddressCreate) -> Address:
        db_obj = Address(**address_in.model_dump(), owner_id=owner_id)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Address]:
        statement = select(Address).where(Address.owner_id == owner_id, Address.deleted_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_default(self, owner_id: uuid.UUID) -> Address | None:
        statement = select(Address).where(
            Address.deleted_at.is_(None),
            Address.owner_id == owner_id,
            Address.is_default,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def clear_default(self, owner_id: uuid.UUID) -> Address | None:
        """Clear default flag for all user addresses"""
        addresses = await self.get_by_owner(owner_id)
        for addr in addresses:
            if addr.is_default:
                addr.is_default = False
                self.session.add(addr)

    async def set_default(self, address_id: uuid.UUID, owner_id: uuid.UUID) -> Address | None:
        """set default flag for all user addresses"""
        await self.clear_default(owner_id)
        address = await self.get(address_id)
        address.is_default = True
        self.session.add(address)
        await self.session.commit()
        await self.session.refresh(address)
        return address
