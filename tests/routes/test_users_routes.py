import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.security import verify_password
from app.models.models import User, UserCreate, UserRole
from app.repositories.user import UserRepo
from app.services.users import UserService
from tests.utils.utils import random_email, random_lower_string

# GET CURRENT USER


async def test_get_users_admin_me(client: AsyncClient, admin_token_headers: dict[str, str]) -> None:
    r = await client.get(f"{settings.API_V1_STR}/users/me", headers=admin_token_headers)
    assert r.status_code == 200
    current_user = r.json()
    assert current_user
    assert current_user["data"]["is_active"] is True
    assert current_user["data"]["role"] == "admin"
    assert current_user["data"]["email"] == settings.ADMIN


async def test_get_users_normal_user_me(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
    r = await client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    assert r.status_code == 200
    current_user = r.json()
    assert current_user
    assert current_user["data"]["is_active"] is True
    assert current_user["data"]["role"] != "admin"


# GET EXISTING USER


async def test_get_existing_user(client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession) -> None:
    service = UserService(repo=UserRepo(session=db))

    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = await service.create_user(user_in=user_in)
    user_id = user.id

    r = await client.get(f"{settings.API_V1_STR}/users/{user_id}", headers=admin_token_headers)
    assert 200 <= r.status_code < 300
    api_user = r.json()["data"]
    existing_user = await service.get_user_by_email(email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


async def test_get_existing_user_current_user(client: AsyncClient, db: AsyncSession) -> None:
    service = UserService(repo=UserRepo(session=db))

    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = await service.create_user(user_in=user_in)
    user_id = user.id

    login_data = {"username": username, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = await client.get(f"{settings.API_V1_STR}/users/{user_id}", headers=headers)
    assert 200 <= r.status_code < 300
    api_user = r.json()["data"]
    existing_user = await service.get_user_by_email(email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


async def test_get_existing_user_permissions_error(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = await client.get(f"{settings.API_V1_STR}/users/{uuid.uuid4()}", headers=normal_user_token_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "The user doesn't have enough privileges"


# CREATE USERS


async def test_create_user_existing_username(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession
) -> None:
    service = UserService(repo=UserRepo(session=db))

    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    await service.create_user(user_in=user_in)

    data = {"email": username, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/users/", headers=admin_token_headers, json=data)
    assert r.status_code == 400
    created_user = r.json()
    assert "id" not in created_user.get("data", {})


async def test_create_user_by_normal_user(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
    username = random_email()
    password = random_lower_string()
    data = {"email": username, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/users/", headers=normal_user_token_headers, json=data)
    assert r.status_code == 403


# RETRIEVE USERS LIST


async def test_retrieve_users(client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession) -> None:
    service = UserService(repo=UserRepo(session=db))

    # Create 2 users
    await service.create_user(UserCreate(email=random_email(), password=random_lower_string()))
    await service.create_user(UserCreate(email=random_email(), password=random_lower_string()))

    r = await client.get(f"{settings.API_V1_STR}/users/", headers=admin_token_headers)
    assert r.status_code == 200
    all_users = r.json()

    assert len(all_users["data"]["users"]) > 1
    assert "pagination" in all_users["data"]
    for item in all_users["data"]["users"]:
        assert "email" in item


# UPDATE USERS


async def test_update_user_me(client: AsyncClient, normal_user_token_headers: dict[str, str], db: AsyncSession) -> None:
    full_name = "Updated Name"
    email = random_email()
    data = {"full_name": full_name, "email": email}
    r = await client.patch(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers, json=data)
    assert r.status_code == 200
    updated_user = r.json()["data"]
    assert updated_user["email"] == email
    assert updated_user["full_name"] == full_name

    user_query = select(User).where(User.email == email)
    result = await db.execute(user_query)
    user_db = result.scalar_one_or_none()
    assert user_db
    assert user_db.email == email
    assert user_db.full_name == full_name


async def test_update_password_me(client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession) -> None:
    new_password = random_lower_string()
    data = {"old_password": settings.ADMIN_PASSWORD, "new_password": new_password}
    r = await client.patch(f"{settings.API_V1_STR}/users/me/password", headers=admin_token_headers, json=data)
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["message"] == "Password updated successfully"

    # Verify in DB
    user_query = select(User).where(User.email == settings.ADMIN)
    result = await db.execute(user_query)
    user_db = result.scalar_one_or_none()
    assert user_db
    assert verify_password(new_password, user_db.hashed_password)

    # Revert to original password
    revert_data = {"old_password": new_password, "new_password": settings.ADMIN_PASSWORD}
    r = await client.patch(f"{settings.API_V1_STR}/users/me/password", headers=admin_token_headers, json=revert_data)
    await db.refresh(user_db)
    assert r.status_code == 200
    assert verify_password(settings.ADMIN_PASSWORD, user_db.hashed_password)


# DELETE USERS


async def test_delete_user_me(client: AsyncClient, db: AsyncSession) -> None:
    """
    Ensure a normal user can delete their own account.
    """
    # --- Create a non-admin user ---
    service = UserService(repo=UserRepo(session=db))
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.CUSTOMER)
    user = await service.create_user(user_in=user_in)
    print(user.role)
    await db.commit()
    user_id = user.id

    # --- Log in as the user ---
    login_data = {"username": email, "password": password}
    r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # --- Call DELETE /users/me ---
    r = await client.delete(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["message"] == "User deleted successfully"

    # --- Confirm user no longer exists in DB ---
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is not None
    assert deleted_user.deleted_at is not None


async def test_delete_user_me_as_admin(client: AsyncClient, admin_token_headers: dict[str, str]) -> None:
    r = await client.delete(f"{settings.API_V1_STR}/users/me", headers=admin_token_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "admin users are not allowed to delete themselves"


# DELETE OTHER USERS


async def test_delete_user_admin_user(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession
) -> None:
    service = UserService(repo=UserRepo(session=db))
    username = random_email()
    password = random_lower_string()
    user = await service.create_user(UserCreate(email=username, password=password))
    user_id = user.id

    r = await client.delete(f"{settings.API_V1_STR}/users/{user_id}", headers=admin_token_headers)
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is not None
    assert deleted_user.deleted_at is not None


async def test_delete_user_not_found(client: AsyncClient, admin_token_headers: dict[str, str]) -> None:
    r = await client.delete(f"{settings.API_V1_STR}/users/{uuid.uuid4()}", headers=admin_token_headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


async def test_delete_user_current_admin_user_error(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession
) -> None:
    service = UserService(repo=UserRepo(session=db))
    admin_user = await service.get_user_by_email(email=settings.ADMIN)
    assert admin_user
    user_id = admin_user.id

    r = await client.delete(f"{settings.API_V1_STR}/users/{user_id}", headers=admin_token_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "admin users are not allowed to delete themselves"


async def test_delete_user_without_privileges(
    client: AsyncClient, normal_user_token_headers: dict[str, str], db: AsyncSession
) -> None:
    service = UserService(repo=UserRepo(session=db))
    username = random_email()
    password = random_lower_string()
    user = await service.create_user(UserCreate(email=username, password=password))

    r = await client.delete(f"{settings.API_V1_STR}/users/{user.id}", headers=normal_user_token_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "Not enough permissions"
