# backend/app/services/address.py
import uuid

from fastapi import HTTPException, status

from app.models.models import (
    AddressCreate,
    AddressesPublic,
    AddressPublic,
    AddressUpdate,
)
from app.repositories.address import AddressRepo


class AddressService:
    def __init__(self, repo: AddressRepo):
        self.repo = repo

    async def create_address(self, owner_id: uuid.UUID, address_in: AddressCreate) -> AddressPublic:
        address = await self.repo.create_address(owner_id=owner_id, address_in=address_in)
        return AddressPublic.model_validate(address)

    async def get_address(self, address_id: uuid.UUID, owner_id: uuid.UUID) -> AddressPublic:
        address = await self.repo.get(address_id)
        if not address or address.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
        return AddressPublic.model_validate(address)

    async def list_user_addresses(self, owner_id: uuid.UUID) -> AddressesPublic:
        addresses = await self.repo.get_by_owner(owner_id)
        addresses = [AddressPublic.model_validate(a) for a in addresses]
        count = len(addresses)
        return AddressesPublic(addresses=addresses, count=count)

    async def update_address(
        self, address_id: uuid.UUID, owner_id: uuid.UUID, address_in: AddressUpdate
    ) -> AddressesPublic:
        address = await self.repo.get(address_id)
        if not address or address.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
        if address_in.is_default:
            await self.repo.clear_default(owner_id)
        address = await self.repo.update(db_obj=address, obj_in=address_in)
        return AddressPublic.model_validate(address)

    async def set_default(self, address_id: uuid.UUID, owner_id: uuid.UUID) -> AddressPublic:
        address = await self.repo.set_default(address_id=address_id, owner_id=owner_id)
        return AddressPublic.model_validate(address)

    async def delete_address(self, address_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        address = await self.get_address(address_id, owner_id)
        await self.repo.soft_delete(id=address.id)
