# backend/app/api/main.py

from fastapi import APIRouter

from app.api.routes import (
    address,
    auth,
    healthz,
    users,
)

api_router = APIRouter()

api_router.include_router(users.users_router)
api_router.include_router(auth.auth_router)
api_router.include_router(address.addresses_router)
api_router.include_router(healthz.health_router)
