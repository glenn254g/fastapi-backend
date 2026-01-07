import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AddressCreate
from app.repositories.address import AddressRepo
from tests.utils.address import create_random_address
from tests.utils.user import create_random_user


@pytest.mark.addresses
class TestAddressRepository:
    """Unit tests for AddressRepo"""

    async def test_create_address(self, db: AsyncSession):
        """Should create address successfully."""
        repo = AddressRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        address_in = AddressCreate(
            street_address="123 Test Street",
            city="Nairobi",
            county="Nairobi",
        )
        address = await repo.create_address(owner_id=user.id, address_in=address_in)
        await db.commit()
        assert address.street_address == "123 Test Street"
        assert address.owner_id == user.id

    async def test_get_by_owner(self, db: AsyncSession):
        """Should retrieve all addresses for an owner."""
        repo = AddressRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        await create_random_address(db, owner_id=user.id)
        await create_random_address(db, owner_id=user.id)
        await create_random_address(db, owner_id=user.id)
        await db.commit()

        addresses = await repo.get_by_owner(user.id)
        assert len(addresses) == 3
        assert all(a.owner_id == user.id for a in addresses)

    async def test_get_default(self, db: AsyncSession):
        """Should retrieve default address for owner."""
        repo = AddressRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        await create_random_address(db, owner_id=user.id, is_default=False)
        default_address = await create_random_address(db, owner_id=user.id, is_default=True)
        await db.commit()

        retrieved = await repo.get_default(user.id)
        assert retrieved is not None
        assert retrieved.id == default_address.id
        assert retrieved.is_default is True

    async def test_set_default(self, db: AsyncSession):
        """Should set an address as default."""
        repo = AddressRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        address1 = await create_random_address(db, owner_id=user.id, is_default=True)  # noqa: F841
        address2 = await create_random_address(db, owner_id=user.id, is_default=False)
        await db.commit()

        updated = await repo.set_default(address2.id, user.id)
        await db.commit()
        assert updated.is_default is True

        # Verify old default is cleared
        addresses = await repo.get_by_owner(user.id)
        default_addresses = [a for a in addresses if a.is_default]
        assert len(default_addresses) == 1
        assert default_addresses[0].id == address2.id

    async def test_clear_default(self, db: AsyncSession):
        """Should clear default flag from all user addresses."""
        repo = AddressRepo(session=db)
        user = await create_random_user(db)
        await db.commit()

        await create_random_address(db, owner_id=user.id, is_default=True)
        await create_random_address(db, owner_id=user.id, is_default=False)
        await db.commit()

        await repo.clear_default(user.id)
        await db.commit()

        addresses = await repo.get_by_owner(user.id)
        assert all(not a.is_default for a in addresses)
