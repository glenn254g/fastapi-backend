import uuid
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Column, Field, Index, Relationship, SQLModel

T = TypeVar("T")


class UserRole(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    MANAGER = "manager"
    ADMIN = "admin"


# GENERIC RESPONSE MODELS
class ResponseModel(SQLModel, Generic[T]):
    """Generic API response wrapper."""

    success: bool = True
    message: str = "Operation successful"
    data: T | None = None


class PaginationMeta(SQLModel):
    """Pagination metadata"""

    total: int
    page: int
    page_size: int
    total_pages: int


class UserFilters(SQLModel):
    is_active: bool | None = None
    is_verified: bool | None = None
    role: str | None = None


# USER MODELS


class UserBase(SQLModel):
    """Base user fields that can be exposed publicly"""

    email: EmailStr = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=256)
    phone_number: str | None = Field(default=None, max_length=20)
    is_active: bool = Field(default=True, index=True)  # Indexed: used in filters
    is_verified: bool = Field(default=False, index=True)  # Indexed: used in filters
    role: str = Field(default=UserRole.CUSTOMER, max_length=50, index=True)  # Indexed: used in filters


class User(UserBase, table=True):
    """Database model - contains ALL fields including sensitive ones"""

    __tablename__ = "users"
    __table_args__ = (
        # For queries like: WHERE is_active=True AND role='customer'
        Index("idx_user_active_role", "is_active", "role"),
        # For queries like: WHERE is_active=True AND is_verified=True
        Index("idx_user_active_verified", "is_active", "is_verified"),
        # For soft delete queries: WHERE deleted_at IS NULL AND is_active=True
        Index("idx_user_deleted_active", "deleted_at", "is_active"),
        # For email lookups with soft delete check
        Index("idx_user_email_deleted", "email", "deleted_at"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    deleted_at: datetime | None = None
    hashed_password: str
    # Relationships with lazy loading by default (eager load when needed)
    addresses: list["Address"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})


class UserCreate(UserBase):
    """For creating new users"""

    password: str = Field(min_length=8, max_length=40)


class UserUpdate(UserBase):
    """For updating user information"""

    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=256)
    phone_number: str | None = Field(default=None, max_length=20)


class UserUpdateMe(SQLModel):
    """For updating own information"""

    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)


class UserRegister(SQLModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=20)


class UpdatePassword(SQLModel):
    old_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# AUTH / JWT MODELS


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None
    exp: int | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# ADDRESS MODELS


class AddressBase(SQLModel):
    """Base address fields"""

    street_address: str | None = Field(default=None, max_length=255, index=True)
    apartment: str | None = Field(default=None, max_length=100, index=True)
    city: str | None = Field(default=None, max_length=100, index=True)
    county: str | None = Field(default=None, max_length=100, index=True)
    postal_code: str | None = Field(default=None, max_length=20, index=True)
    is_default: bool = Field(default=False, index=True)
    delivery_instructions: str | None = Field(default=None, max_length=500)


class Address(AddressBase, table=True):
    """Database model"""

    __tablename__ = "addresses"
    __table_args__ = (
        # For queries like: WHERE owner_id=? AND is_default=True
        Index("idx_address_owner_default", "owner_id", "is_default"),
        # For queries with soft delete: WHERE owner_id=? AND deleted_at IS NULL
        Index("idx_address_owner_deleted", "owner_id", "deleted_at"),
        # For location-based queries: WHERE city=? AND county=?
        Index("idx_address_location", "city", "county"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    )  # Explicitly indexed for JOIN performance
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
    user: User | None = Relationship(back_populates="addresses")


class AddressCreate(AddressBase):
    """For creating addresses"""

    pass


class AddressPublic(AddressBase):
    """Public address representation"""

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class UserPublic(UserBase):
    """Public user representation - only safe fields"""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    model_config = {"from_attributes": True}


class UsersPublic(SQLModel):
    """Properly nested response for user lists"""

    users: list[UserPublic]
    pagination: PaginationMeta


class AddressesPublic(SQLModel):
    """Public addresses"""

    addresses: list[AddressPublic]
    count: int


class AddressUpdate(AddressBase):
    """For updating addresses"""

    pass


class UserWithAddresses(UserBase):
    """Public nested user representation - only safe fields"""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    addresses: list[AddressPublic] = []
    model_config = {"from_attributes": True}


class NestedUsersPublic(SQLModel):
    """Public user representation - only safe fields"""

    users: list[UserWithAddresses]
    pagination: PaginationMeta
