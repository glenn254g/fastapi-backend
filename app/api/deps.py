# backend/app/api/deps.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_async_session
from app.models.models import TokenPayload, User, UserRole
from app.repositories.address import AddressRepo
from app.repositories.user import UserRepo
from app.services.address import AddressService
from app.services.users import UserService

# OAuth2 dependency
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")

# Async session dependency
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """Get the current authenticated user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    user = await session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: str):
    """Dependency factory for role-based access control."""

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user

    return role_checker


CurrentAdmin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
CurrentCustomer = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]
CurrentAdminOrManager = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


# REPOSITORY DEPENDENCIES
async def get_user_repo(session: SessionDep) -> UserRepo:
    """Get user repository instance."""
    return UserRepo(session)


async def get_address_repo(session: SessionDep) -> AddressRepo:
    """Get address repository instance."""
    return AddressRepo(session)


UserRepoDep = Annotated[UserRepo, Depends(get_user_repo)]
AddressRepoDep = Annotated[AddressRepo, Depends(get_address_repo)]


# SERVICE DEPENDENCIES
async def get_user_service(repo: UserRepoDep) -> UserService:
    """Get user service instance with injected user repository."""
    return UserService(repo)


async def get_address_service(repo: AddressRepoDep) -> AddressService:
    """Get address service instance with injected address repository."""
    return AddressService(repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]
