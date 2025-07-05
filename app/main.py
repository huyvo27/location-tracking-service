from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.router import base_router, v1_router, ws_router
from app.custom_docs import configure_docs
from app.db.base import Base
from app.db.redis import close_redis_clients
from app.db.session import close_db_engine, engine
from app.initialization import setup_system_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await setup_system_admin()
    yield

    await close_redis_clients()


def get_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(base_router, prefix=f"{settings.API_PREFIX}")
    app.include_router(v1_router, prefix=f"{settings.API_PREFIX}/v1")
    app.include_router(ws_router, prefix="")

    register_exception_handlers(app)

    app = configure_docs(app)

    return app


app = get_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
