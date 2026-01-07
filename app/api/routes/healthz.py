# backend/app/api/routes/healthz.py
from fastapi import APIRouter

health_router = APIRouter(prefix="/utils", tags=["utils"])


@health_router.get("/health-check/")
async def health_check() -> bool:
    return True
