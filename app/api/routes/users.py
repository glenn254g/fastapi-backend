# backend/app/api/routes/users.py
import uuid

from fastapi import APIRouter, Query

from app.api.deps import (
    CurrentAdmin,
    CurrentAdminOrManager,
    CurrentUser,
    UserServiceDep,
)
from app.models.models import (
    ResponseModel,
    UpdatePassword,
    UserCreate,
    UserFilters,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)

users_router = APIRouter(tags=["Users"], prefix="/users")


@users_router.post("/", response_model=ResponseModel[UserPublic])
async def create_user(user_in: UserCreate, service: UserServiceDep, _: CurrentAdmin) -> ResponseModel[UserPublic]:
    """Admin only: Create a new user"""
    user = await service.create_user(user_in=user_in)
    return ResponseModel(data=user)


@users_router.post("/signup", response_model=ResponseModel[UserPublic])
async def register_user(user_in: UserRegister, service: UserServiceDep) -> ResponseModel[UserPublic]:
    """Public endpoint: Register a new user"""
    user = await service.create_user(user_in=user_in)
    return ResponseModel(data=user, message="User registered successfully")


@users_router.get("/me", response_model=ResponseModel[UserPublic])
async def get_current_user(current_user: CurrentUser, service: UserServiceDep) -> ResponseModel[UserPublic]:
    """Get current authenticated user"""
    user = await service.get_user_by_id(user_id=current_user.id)
    return ResponseModel(data=user)


@users_router.patch("/me", response_model=ResponseModel[UserPublic])
async def update_me(
    user_in: UserUpdateMe,
    service: UserServiceDep,
    current_user: CurrentUser,
) -> ResponseModel[UserPublic]:
    """Update own user information"""
    user = await service.update_user(user_id=current_user.id, user_in=user_in)
    return ResponseModel(data=user)


@users_router.patch("/me/password", response_model=ResponseModel)
async def update_password_me(
    password_in: UpdatePassword,
    service: UserServiceDep,
    current_user: CurrentUser,
) -> ResponseModel:
    """Update own password"""
    await service.change_password(
        user=current_user,
        old_password=password_in.old_password,
        new_password=password_in.new_password,
    )
    return ResponseModel(message="Password updated successfully")


@users_router.delete("/me", response_model=ResponseModel)
async def delete_user_me(
    service: UserServiceDep,
    current_user: CurrentUser,
) -> ResponseModel:
    """Delete own user account"""
    await service.delete_user_me(user=current_user)
    return ResponseModel(message="User deleted successfully")


@users_router.get("/", response_model=ResponseModel[UsersPublic])
async def list_users(
    _: CurrentAdminOrManager,
    service: UserServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    is_verified: bool | None = None,
    role: str | None = None,
) -> ResponseModel[UsersPublic]:
    """Admin/Manager only: List all users"""
    filters = UserFilters(is_active=is_active, is_verified=is_verified, role=role)
    result = await service.list_users(filters, page, page_size)
    return ResponseModel(
        message=f"Retrieved {len(result.users)} users out of {result.pagination.total}",
        data=result,
    )


@users_router.get("/{user_id}", response_model=ResponseModel[UserPublic])
async def get_user_by_id(
    user_id: uuid.UUID, service: UserServiceDep, current_user: CurrentUser
) -> ResponseModel[UserPublic]:
    """Get user by ID - users can get their own data, admins can get any user"""
    from app.models.models import UserRole

    # Allow users to get their own data, or admins to get any user
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")

    user = await service.get_user_by_id(user_id)
    return ResponseModel(data=user)


@users_router.patch("/{user_id}", response_model=ResponseModel[UserPublic])
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    service: UserServiceDep,
    _: CurrentAdmin,
) -> ResponseModel[UserPublic]:
    """Admin only: Update any user"""
    user = await service.update_user(user_id, user_in)
    return ResponseModel(data=user)


@users_router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(user_id: uuid.UUID, service: UserServiceDep, current_admin: CurrentAdmin) -> ResponseModel:
    """Admin only: Delete any user"""
    await service.delete_user(user_id, current_admin.id)
    return ResponseModel(message="User deleted successfully")


# # backend/app/api/routes/users.py
# import uuid

# import click
# from fastapi import APIRouter, Query

# from app.api.deps import (
#     CurrentAdmin,
#     CurrentAdminOrManager,
#     CurrentUser,
#     UserServiceDep,
# )
# from app.core.logger import log_panel, log_section, logger
# from app.models.models import (
#     ResponseModel,
#     UserCreate,
#     UserFilters,
#     UserPublic,
#     UsersPublic,
#     UserUpdate,
#     UserUpdateMe,
# )

# users_router = APIRouter(tags=["Users"], prefix="/users")


# @users_router.post("/", response_model=ResponseModel[UserPublic])
# async def create_user(
#     user_in: UserCreate, service: UserServiceDep, _: CurrentAdmin
# ) -> ResponseModel[UserPublic]:
#     """
#     Create a new user (Admin only).
#     Enhanced with rich logging and validation feedback.
#     """
#     log_section("🆕 CREATE USER ENDPOINT", style="green")
#     logger.info(f"Admin creating user | email={user_in.email} | role={user_in.role}")
#     user = await service.create_user(user_in)
#     # Beautiful success message
#     success_msg = (
#         f"✓ User Created\n\n"
#         f"ID: {user.id}\n"
#         f"Email: {click.style(user.email, fg='cyan', bold=True)}\n"
#         f"Role: {click.style(user.role, fg='yellow')}\n"
#         f"Status: {click.style('Active' if user.is_active else 'Inactive', fg='green' if user.is_active else 'red')}"
#     )
#     log_panel(success_msg, title="User Creation Success", style="success")
#     return ResponseModel(message=f"User created successfully with role {user.role}", data=user)


# @users_router.get("/me", response_model=ResponseModel[UserPublic])
# async def get_current_user(
#     current_user: CurrentUser, service: UserServiceDep
# ) -> ResponseModel[UserPublic]:
#     """
#     Get current authenticated user's profile.
#     """
#     log_section("👤 GET CURRENT USER", style="cyan")
#     logger.info(f"User fetching own profile | user_id={current_user.id}")
#     user = await service.get_user_by_id(current_user.id)
#     logger.success(f"✓ Profile retrieved | email={user.email}")
#     return ResponseModel(data=user)


# @users_router.put("/me", response_model=ResponseModel[UserPublic])
# async def update_me(
#     user_in: UserUpdateMe,
#     service: UserServiceDep,
#     current_user: CurrentUser,
# ) -> ResponseModel[UserPublic]:
#     """
#     Update current user's own profile.
#     """
#     log_section("✏️  UPDATE PROFILE", style="yellow")
#     logger.info(
#         f"User updating own profile | user_id={current_user.id} | "
#         f"changes={user_in.model_dump(exclude_unset=True)}"
#     )
#     user = await service.update_user(current_user.id, user_in)
#     log_panel(
#         f"Profile updated\nEmail: {user.email}\nName: {user.full_name or 'Not set'}",
#         title="Update Success",
#         style="success",
#     )
#     return ResponseModel(message="Profile updated successfully", data=user)


# @users_router.get("/", response_model=ResponseModel[UsersPublic])
# async def list_users(
#     _: CurrentAdminOrManager,
#     service: UserServiceDep,
#     page: int = Query(1, ge=1, description="Page number"),
#     page_size: int = Query(20, ge=1, le=100, description="Items per page"),
#     is_active: bool | None = Query(None, description="Filter by active status"),
#     is_verified: bool | None = Query(None, description="Filter by verified status"),
#     role: str | None = Query(None, description="Filter by role"),
# ) -> ResponseModel[UsersPublic]:
#     """
#     List all users with filtering and pagination (Admin/Manager only).
#     Enhanced with detailed query logging.
#     """
#     log_section("📋 LIST USERS", style="magenta")
#     # Log query parameters beautifully
#     filter_summary = []
#     if is_active is not None:
#         filter_summary.append(f"Active: {click.style(str(is_active), fg='cyan')}")
#     if is_verified is not None:
#         filter_summary.append(f"Verified: {click.style(str(is_verified), fg='cyan')}")
#     if role:
#         filter_summary.append(f"Role: {click.style(role, fg='yellow')}")
#     if filter_summary:
#         logger.info(
#             f"Listing users with filters | page={page} | page_size={page_size} | "
#             f"filters=[{', '.join(filter_summary)}]"
#         )
#     else:
#         logger.info(f"Listing all users | page={page} | page_size={page_size}")
#     filters = UserFilters(is_active=is_active, is_verified=is_verified, role=role)
#     result = await service.list_users(filters, page, page_size)
#     # Rich success message with stats
#     stats_msg = (
#         f"📊 Query Results\n\n"
#         f"Returned: {click.style(str(len(result.users)), fg='cyan', bold=True)} users\n"
#         f"Total: {click.style(str(result.pagination.total), fg='green')} users\n"
#         f"Page: {click.style(f'{page}/{result.pagination.total_pages}', fg='yellow')}"
#     )
#     log_panel(stats_msg, title="Users Retrieved", style="info")
#     return ResponseModel(
#         message=f"Retrieved {len(result.users)} users out of {result.pagination.total}", data=result
#     )


# @users_router.get("/{user_id}", response_model=ResponseModel[UserPublic])
# async def get_user_by_id(
#     user_id: uuid.UUID, service: UserServiceDep, _: CurrentAdmin
# ) -> ResponseModel[UserPublic]:
#     """
#     Get a specific user by ID (Admin only).
#     """
#     log_section("🔍 GET USER BY ID", style="cyan")
#     logger.info(f"Admin fetching user | user_id={user_id}")
#     user = await service.get_user_by_id(user_id)
#     logger.success(f"✓ User retrieved | email={user.email}")
#     return ResponseModel(data=user)


# @users_router.put("/{user_id}", response_model=ResponseModel[UserPublic])
# async def update_user(
#     user_id: uuid.UUID, user_in: UserUpdate, service: UserServiceDep, _: CurrentAdmin
# ) -> ResponseModel[UserPublic]:
#     """
#     Update any user (Admin only).
#     """
#     log_section("✏️  ADMIN UPDATE USER", style="yellow")
#     changes = user_in.model_dump(exclude_unset=True)
#     logger.info(f"Admin updating user | user_id={user_id} | changes={list(changes.keys())}")
#     user = await service.update_user(user_id, user_in)
#     log_panel(
#         f"User {user.email} updated by admin\nUpdated fields: {', '.join(changes.keys())}",
#         title="Admin Update Success",
#         style="success",
#     )
#     return ResponseModel(message="User updated successfully", data=user)


# @users_router.delete("/{user_id}", response_model=ResponseModel)
# async def delete_user(
#     user_id: uuid.UUID, service: UserServiceDep, current_admin: CurrentAdmin
# ) -> ResponseModel:
#     """
#     Soft delete a user (Admin only).
#     """
#     log_section("🗑️  DELETE USER", style="red")
#     logger.warning(f"Admin deleting user | user_id={user_id} | admin_id={current_admin.id}")
#     await service.delete_user(user_id, current_admin.id)
#     log_panel(
#         f"User deleted successfully\nUser ID: {user_id}\nDeleted by: {current_admin.email}",
#         title="⚠️  Deletion Complete",
#         style="warning",
#     )
#     return ResponseModel(message="User deleted successfully")
