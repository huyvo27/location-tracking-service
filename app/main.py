from asyncio import to_thread
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.router import v1_router
from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.db import Base, engine
from app.custom_docs import configure_docs
from app.initialization import setup_system_admin


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await to_thread(setup_system_admin)
    yield


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

    app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

    app.include_router(v1_router, prefix=f"{settings.API_PREFIX}/v1")

    register_exception_handlers(app)

    app = configure_docs(app)

    return app


app = get_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
