import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.main import api_router
from app.core.config import settings
from app.core.logger import logger  # noqa: F401


def custom_generate_unique_id(route: APIRoute) -> str:
    """Generate unique operation IDs for OpenAPI."""
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Application lifespan manager"""
#     logger.info("placeholder")


def get_application() -> FastAPI:
    """Create FastAPI application with all configurations."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        #description=settings.API_DESCRIPTION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        generate_unique_id_function=custom_generate_unique_id,
        # lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app


app = get_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
