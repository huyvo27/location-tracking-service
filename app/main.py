from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.router import router
from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.db import Base, engine
from app.initialization import setup_admin_user


Base.metadata.create_all(bind=engine)


def get_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        docs_url="/docs",
        redoc_url="/re-docs",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)
    app.include_router(router, prefix=settings.API_PREFIX)
    register_exception_handlers(app)

    return app


app = get_app()


@app.on_event("startup")
async def startup():
    setup_admin_user()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
