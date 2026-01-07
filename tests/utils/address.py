# tests/utils/address.py
"""
Address-related test utilities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Address, AddressCreate
from app.repositories.address import AddressRepo
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


async def create_random_address(db: AsyncSession, owner_id: str = None, **kwargs) -> Address:
    repo = AddressRepo(db)

    if not owner_id:
        user = await create_random_user(db)
        owner_id = user.id

    address_in = AddressCreate(
        street_address=kwargs.get("street_address", f"{random_lower_string(10)} Street"),
        apartment=kwargs.get("apartment", f"Apt {random_lower_string(5)}"),
        city=kwargs.get("city", "Nairobi"),
        county=kwargs.get("county", "Nairobi"),
        postal_code=kwargs.get("postal_code", "00100"),
        is_default=kwargs.get("is_default", False),
        delivery_instructions=kwargs.get("delivery_instructions", "Ring the bell"),
    )

    address = await repo.create_address(owner_id=owner_id, address_in=address_in)
    await db.flush()
    await db.refresh(address)
    await db.refresh(address.user)
    return address
