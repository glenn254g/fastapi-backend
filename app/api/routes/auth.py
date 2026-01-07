# backend/app/api/routes/auth.py

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    CurrentUser,
    SessionDep,
    UserServiceDep,
)
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.models import ResponseModel, Token, UserPublic, UserRegister
from app.repositories.user import UserRepo

auth_router = APIRouter(tags=["authentication"], prefix="/auth")


@auth_router.post("/register", response_model=ResponseModel[UserPublic])
async def register(
    user_in: UserRegister,
    service: UserServiceDep,
) -> ResponseModel[UserPublic]:
    user = await service.create_user(user_in)
    return ResponseModel(data=user)


@auth_router.post("/login/access-token", response_model=Token)
async def log_in(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    repo = UserRepo(session)
    user = await repo.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=expires_delta)
    return Token(access_token=access_token)


@auth_router.post("/login/test-token", response_model=ResponseModel[UserPublic])
async def test_token(
    current_user: CurrentUser, service: UserServiceDep
) -> ResponseModel[UserPublic]:
    current_user = await service.get_user_by_id(current_user.id)
    return ResponseModel(data=current_user)


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(current_user: CurrentUser) -> Token:
    """Generate a new access token for the current user"""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(current_user.id, expires_delta=expires_delta)
    return Token(access_token=access_token)


@auth_router.post("/logout", response_model=ResponseModel)
async def logout() -> ResponseModel:
    return ResponseModel(message="Successfully logged out")
