# backend/tests/routes/test_address_routes.py

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import (
    Address,
    AddressCreate,
    AddressUpdate,
    UserCreate,
)
from app.repositories.address import AddressRepo
from app.repositories.user import UserRepo
from app.services.address import AddressService
from app.services.users import UserService
from tests.utils.utils import (
    random_email,
    random_lower_string,
)

# CREATE ADDRESS


async def test_create_address(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test creating a new address"""
    data = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["street_address"] == "427"
    assert result["data"]["city"] == "Daystar"
    assert result["data"]["is_default"] is True
    assert "id" in result["data"]


async def test_create_address_minimal(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    """Test creating address with minimal required fields"""
    data = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["street_address"] == "427"
    assert result["data"]["apartment"] == "Heri"
    assert result["data"]["postal_code"] is None


async def test_create_address_unauthorized(
    client: AsyncClient,
) -> None:
    """Test creating address without authentication"""
    data = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        json=data,
    )
    assert r.status_code == 401


async def test_create_multiple_addresses(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    """Test creating multiple addresses for same user"""
    addresses = [
        {
            "street_address": "First St",
            "city": "Nairobi-cbd",
            "county": "Nairobi",
            "is_default": True,
        },
        {
            "street_address": "Second St",
            "city": "Mombasa",
            "county": "Mombasa",
            "is_default": False,
        },
    ]

    for address in addresses:
        r = await client.post(
            f"{settings.API_V1_STR}/addresses/",
            headers=normal_user_token_headers,
            json=address,
        )
        assert r.status_code == 200


# LIST USER ADDRESSES


async def test_list_user_addresses(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test listing all addresses for current user"""
    # Create test addresses
    for i in range(3):
        address = AddressCreate(
            street_address=f"Street {i}",
            city=f"City {i}",
            county=f"County {i}",
            is_default=(i == 0),
        )
        r = await client.post(
            f"{settings.API_V1_STR}/addresses/",
            headers=normal_user_token_headers,
            json=address.model_dump(exclude_unset=True),
        )
    r = await client.get(
        f"{settings.API_V1_STR}/addresses/me",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["count"] >= 3
    assert "addresses" in result["data"]
    assert len(result["data"]["addresses"]) >= 3


async def test_list_addresses_empty(client: AsyncClient, db: AsyncSession) -> None:
    """Test listing addresses when user has none"""
    # Create new user with no addresses
    service = UserService(repo=UserRepo(session=db))
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    await service.create_user(user_in=user_in)

    # Login
    login_data = {
        "username": email,
        "password": password,
    }
    r = await client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data=login_data,
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List addresses
    r = await client.get(
        f"{settings.API_V1_STR}/addresses/me",
        headers=headers,
    )

    assert r.status_code == 200
    result = r.json()
    assert result["data"]["count"] == 0
    assert result["data"]["addresses"] == []


async def test_list_addresses_unauthorized(
    client: AsyncClient,
) -> None:
    """Test listing addresses without authentication"""
    r = await client.get(f"{settings.API_V1_STR}/addresses/me")
    assert r.status_code == 401


# GET SINGLE ADDRESS


async def test_get_address(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test getting a specific address"""
    # create user
    user_service = UserService(repo=UserRepo(session=db))
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = await user_service.create_user(user_in=user_in)

    # create user's address
    address_service = AddressService(repo=AddressRepo(session=db))
    address_in = AddressCreate(
        street_address="Get Test St",
        city="Nairobi",
        county="Nairobi",
    )
    address = await address_service.create_address(
        owner_id=user.id,
        address_in=address_in,
    )

    login_data = {
        "username": username,
        "password": password,
    }
    r = await client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data=login_data,
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # get users address
    r = await client.get(
        f"{settings.API_V1_STR}/addresses/{address.id}",
        headers=headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["id"] == str(address.id)
    assert result["data"]["street_address"] == "Get Test St"


async def test_get_address_not_found(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    """Test getting non-existent address"""
    r = await client.get(f"{settings.API_V1_STR}/addresses/{uuid.uuid4()}", headers=normal_user_token_headers)
    assert r.status_code == 404


async def test_get_address_wrong_owner(client: AsyncClient, db: AsyncSession) -> None:
    """Test getting address owned by another user"""
    # Create two users
    service = UserService(repo=UserRepo(session=db))
    addr_service = AddressService(repo=AddressRepo(session=db))

    # User 1 with address
    email1 = random_email()
    user1 = await service.create_user(
        UserCreate(
            email=email1,
            password=random_lower_string(),
        )
    )
    addr_data = AddressCreate(street_address="User1 St", city="City1", county="County1")
    address = await addr_service.create_address(user1.id, addr_data)

    # User 2 trying to access
    email2 = random_email()
    password2 = random_lower_string()
    await service.create_user(UserCreate(email=email2, password=password2))

    # Login as user 2
    login_data = {
        "username": email2,
        "password": password2,
    }
    r = await client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data=login_data,
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to get user1's address
    r = await client.get(
        f"{settings.API_V1_STR}/addresses/{address.id}",
        headers=headers,
    )
    assert r.status_code == 404


# UPDATE ADDRESS


async def test_update_address(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test updating an address"""
    # create user's address
    data = AddressCreate(
        street_address="427", apartment="Heri", city="Daystar", county="Machakos", is_default=True
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=data,
    )
    result = r.json()
    address_id = result["data"]["id"]

    update_data = AddressUpdate(
        street_address="New Street",
        city="New City",
        county="Nairobi",
        postal_code="12345",
    ).model_dump(exclude_unset=True)

    # update users address
    r = await client.put(
        f"{settings.API_V1_STR}/addresses/{address_id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["street_address"] == "New Street"
    assert result["data"]["city"] == "New City"
    assert result["data"]["postal_code"] == "12345"


async def test_update_address_partial(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test partial update of address"""
    # create user address
    address = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=address,
    )
    result = r.json()
    address_id = result["data"]["id"]

    update_data = AddressUpdate(postal_code="12345").model_dump(exclude_unset=True)
    r = await client.put(
        f"{settings.API_V1_STR}/addresses/{address_id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["street_address"] == "427"
    assert result["data"]["postal_code"] == "12345"


async def test_update_address_not_found(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    """Test updating non-existent address"""
    update_data = {"street_address": "New Street"}

    r = await client.put(
        f"{settings.API_V1_STR}/addresses/{uuid.uuid4()}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert r.status_code == 404


# DELETE ADDRESS


async def test_delete_address(client: AsyncClient, db: AsyncSession) -> None:
    """Test soft deleting an address"""
    # create a user
    user_service = UserService(repo=UserRepo(session=db))
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = await user_service.create_user(user_in=user_in)

    # create user's address
    address_service = AddressService(repo=AddressRepo(session=db))
    address_in = AddressCreate(
        street_address="427-0100",
        city="Nairobi",
        county="Nairobi",
    )
    address = await address_service.create_address(
        owner_id=user.id,
        address_in=address_in,
    )
    address_id = address.id
    login_data = {
        "username": username,
        "password": password,
    }
    r = await client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data=login_data,
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.delete(
        f"{settings.API_V1_STR}/addresses/{address_id}",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Address deleted"

    # Verify soft delete
    query = select(Address).where(Address.id == address_id)
    result = await db.execute(query)
    deleted_addr = result.scalar_one_or_none()
    assert deleted_addr is not None
    assert deleted_addr.deleted_at is not None


async def test_delete_address_not_found(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    """Test deleting non-existent address"""
    r = await client.delete(
        f"{settings.API_V1_STR}/addresses/{uuid.uuid4()}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 404


async def test_delete_address_unauthorized(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test deleting address without authentication"""
    data = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    ).model_dump(exclude_unset=True)
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=data,
    )
    result = r.json()
    address_id = result["data"]["id"]
    # dont include headers
    r = await client.delete(f"{settings.API_V1_STR}/addresses/{address_id}")
    assert r.status_code == 401


# SET DEFAULT ADDRESS


async def test_set_default_address(
    client: AsyncClient,
    normal_user_token_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    """Test setting an address as default"""

    address_1 = AddressCreate(
        street_address="427",
        apartment="Heri",
        city="Daystar",
        county="Machakos",
        is_default=True,
    )
    addr1 = address_1.model_dump(exclude_unset=True)

    address_2 = AddressCreate(
        street_address="508",
        apartment="oc",
        city="Daystar",
        county="Machakos",
        is_default=False,
    )
    addr2 = address_2.model_dump(exclude_unset=True)

    r1 = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=addr1,
    )
    r1 = r1.json()
    # addr1_id = r1["data"]["id"]

    r2 = await client.post(
        f"{settings.API_V1_STR}/addresses/",
        headers=normal_user_token_headers,
        json=addr2,
    )
    r2 = r2.json()
    addr2_id = r2["data"]["id"]

    # Set addr2 as default
    r = await client.post(
        f"{settings.API_V1_STR}/addresses/{addr2_id}/set-default",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["data"]["is_default"] is True
    assert result["data"]["id"] == str(addr2_id)
    # Verify addr1 is no longer default
    # await db.refresh(address_1)
    # assert address_1.is_default is False


# async def test_set_default_address_not_found(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
#     """Test setting non-existent address as default"""
#     r = await client.post(
#         f"{settings.API_V1_STR}/addresses/{uuid.uuid4()}/set-default",
#         headers=normal_user_token_headers,
#     )
#     assert r.status_code == 404


# async def test_set_default_already_default(client: AsyncClient, normal_user_token_headers: dict[str, str], db: AsyncSession) -> None:
#     """Test setting already-default address as default"""
#     service = AddressService(repo=AddressRepo(session=db))
#     user_service = UserService(repo=UserRepo(session=db))

#     user = await user_service.get_user_by_email(email=settings.ADMIN)

#     addr = await service.create_address(user.id, AddressCreate(street_address="Default", city="C", county="Co", is_default=True))

#     r = await client.post(f"{settings.API_V1_STR}/addresses/{addr.id}/set-default", headers=normal_user_token_headers)

#     assert r.status_code == 200
#     result = r.json()
#     assert result["data"]["is_default"] is True
