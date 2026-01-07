# backend/app/api/routes/address.py
import uuid

from fastapi import APIRouter

from app.api.deps import AddressServiceDep, CurrentUser
from app.models.models import (
    AddressCreate,
    AddressesPublic,
    AddressPublic,
    AddressUpdate,
    ResponseModel,
)

addresses_router = APIRouter(tags=["Addresses"], prefix="/addresses")


@addresses_router.post("/", response_model=ResponseModel[AddressPublic])
async def create_address(
    address_in: AddressCreate, service: AddressServiceDep, current_user: CurrentUser
) -> ResponseModel[AddressPublic]:
    """Create a new address for the current user."""
    address = await service.create_address(current_user.id, address_in)
    return ResponseModel(message=f"Address created in {address.city}", data=address)


@addresses_router.get("/me", response_model=ResponseModel[AddressesPublic])
async def list_user_addresses(
    service: AddressServiceDep, current_user: CurrentUser
) -> ResponseModel[AddressesPublic]:
    """Get all addresses for the current user."""
    addresses = await service.list_user_addresses(current_user.id)
    return ResponseModel(message=f"Found {addresses.count} address(es)", data=addresses)


@addresses_router.get("/{address_id}", response_model=ResponseModel[AddressPublic])
async def get_address(
    address_id: uuid.UUID, service: AddressServiceDep, current_user: CurrentUser
) -> ResponseModel[AddressPublic]:
    """Get a specific address by ID (ownership verified)."""
    address = await service.get_address(address_id, current_user.id)
    return ResponseModel(data=address)


@addresses_router.put("/{address_id}", response_model=ResponseModel[AddressPublic])
async def update_address(
    address_id: uuid.UUID,
    address_in: AddressUpdate,
    service: AddressServiceDep,
    current_user: CurrentUser,
) -> ResponseModel[AddressPublic]:
    """Update an existing address."""
    address = await service.update_address(address_id, current_user.id, address_in)
    return ResponseModel(message="Address updated", data=address)


@addresses_router.delete("/{address_id}", response_model=ResponseModel)
async def delete_address(
    address_id: uuid.UUID, service: AddressServiceDep, current_user: CurrentUser
) -> ResponseModel:
    """Soft delete an address."""
    await service.delete_address(address_id, current_user.id)
    return ResponseModel(message="Address deleted")


@addresses_router.post("/{address_id}/set-default", response_model=ResponseModel[AddressPublic])
async def set_default_address(
    address_id: uuid.UUID, service: AddressServiceDep, current_user: CurrentUser
) -> ResponseModel[AddressPublic]:
    """
    Set an address as the default delivery address.
    This will automatically clear the default flag from other addresses.
    """
    address = await service.set_default(address_id=address_id, owner_id=current_user.id)
    return ResponseModel(message=f"Set {address.city} address as default", data=address)
