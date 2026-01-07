# # backend/tests/routes/test_auth_routes.py

# from httpx import AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.config import settings
# from app.models.models import UserCreate
# from app.repositories.user import UserRepo
# from app.services.users import UserService
# from tests.utils.utils import random_email, random_lower_string


# # ------------------------------
# # REGISTER
# # ------------------------------
# async def test_register_new_user(client: AsyncClient, db: AsyncSession) -> None:
#     """Test successful user registration"""
#     email = random_email()
#     password = random_lower_string()
#     data = {"email": email, "password": password, "full_name": "Test User"}

#     r = await client.post(f"{settings.API_V1_STR}/auth/register", json=data)
#     assert r.status_code == 200
#     result = r.json()
#     assert result["data"]["email"] == email
#     assert result["data"]["full_name"] == "Test User"
#     assert result["data"]["is_active"] is True
#     assert "id" in result["data"]


# async def test_register_duplicate_email(client: AsyncClient, db: AsyncSession) -> None:
#     """Test registration with existing email fails"""
#     service = UserService(repo=UserRepo(session=db))

#     email = random_email()
#     password = random_lower_string()
#     user_in = UserCreate(email=email, password=password)
#     await service.create_user(user_in=user_in)

#     # Try to register with same email
#     data = {"email": email, "password": random_lower_string()}
#     r = await client.post(f"{settings.API_V1_STR}/auth/register", json=data)
#     assert r.status_code == 400


# async def test_register_invalid_email(client: AsyncClient) -> None:
#     """Test registration with invalid email format"""
#     data = {"email": "not-an-email", "password": random_lower_string()}
#     r = await client.post(f"{settings.API_V1_STR}/auth/register", json=data)
#     assert r.status_code == 422


# # ------------------------------
# # LOGIN
# # ------------------------------
# async def test_login_success(client: AsyncClient, db: AsyncSession) -> None:
#     """Test successful login"""
#     service = UserService(repo=UserRepo(session=db))

#     email = random_email()
#     password = random_lower_string()
#     user_in = UserCreate(email=email, password=password)
#     await service.create_user(user_in=user_in)

#     login_data = {"username": email, "password": password}
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)

#     assert r.status_code == 200
#     tokens = r.json()
#     assert "access_token" in tokens
#     assert tokens["token_type"] == "bearer"


# async def test_login_incorrect_password(client: AsyncClient, db: AsyncSession) -> None:
#     """Test login with wrong password"""
#     service = UserService(repo=UserRepo(session=db))

#     email = random_email()
#     password = random_lower_string()
#     user_in = UserCreate(email=email, password=password)
#     await service.create_user(user_in=user_in)

#     login_data = {"username": email, "password": "wrongpassword"}
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)

#     assert r.status_code == 401
#     assert r.json()["detail"] == "Invalid credentials"


# async def test_login_nonexistent_user(client: AsyncClient) -> None:
#     """Test login with non-existent email"""
#     login_data = {"username": random_email(), "password": random_lower_string()}
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)

#     assert r.status_code == 401
#     assert r.json()["detail"] == "Invalid credentials"


# async def test_login_inactive_user(client: AsyncClient, db: AsyncSession) -> None:
#     """Test login with inactive user account"""
#     service = UserService(repo=UserRepo(session=db))

#     email = random_email()
#     password = random_lower_string()
#     user_in = UserCreate(email=email, password=password, is_active=False)
#     await service.create_user(user_in=user_in)

#     login_data = {"username": email, "password": password}
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/access-token", data=login_data)

#     assert r.status_code == 400
#     assert r.json()["detail"] == "Inactive user"


# # ------------------------------
# # TEST TOKEN
# # ------------------------------
# async def test_test_token_valid(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
#     """Test token validation endpoint with valid token"""
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/test-token", headers=normal_user_token_headers)

#     assert r.status_code == 200
#     result = r.json()
#     assert "data" in result
#     assert "email" in result["data"]
#     assert result["data"]["is_active"] is True


# async def test_test_token_invalid(client: AsyncClient) -> None:
#     """Test token validation with invalid token"""
#     headers = {"Authorization": "Bearer invalid_token"}
#     r = await client.post(f"{settings.API_V1_STR}/auth/login/test-token", headers=headers)

#     assert r.status_code == 401


# # ------------------------------
# # REFRESH TOKEN
# # ------------------------------
# async def test_refresh_token(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
#     """Test token refresh endpoint"""
#     r = await client.post(f"{settings.API_V1_STR}/auth/refresh", headers=normal_user_token_headers)

#     assert r.status_code == 200
#     tokens = r.json()
#     assert "access_token" in tokens
#     assert tokens["token_type"] == "bearer"


# async def test_refresh_token_unauthorized(client: AsyncClient) -> None:
#     """Test refresh without authentication"""
#     r = await client.post(f"{settings.API_V1_STR}/auth/refresh")
#     assert r.status_code == 401


# # ------------------------------
# # LOGOUT
# # ------------------------------
# async def test_logout(client: AsyncClient) -> None:
#     """Test logout endpoint"""
#     r = await client.post(f"{settings.API_V1_STR}/auth/logout")

#     assert r.status_code == 200
#     result = r.json()
#     assert result["message"] == "Successfully logged out"


# async def test_logout_authenticated(client: AsyncClient, normal_user_token_headers: dict[str, str]) -> None:
#     """Test logout with authenticated user"""
#     r = await client.post(f"{settings.API_V1_STR}/auth/logout", headers=normal_user_token_headers)

#     assert r.status_code == 200
#     result = r.json()
#     assert result["message"] == "Successfully logged out"
