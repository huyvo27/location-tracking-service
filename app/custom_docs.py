from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse


def generate_filtered_openapi(app: FastAPI, prefix: str, version: str, title: str):
    filtered_routes = [route for route in app.routes if route.path.startswith(prefix)]
    return get_openapi(
        title=title,
        version=version,
        description=app.description,
        routes=filtered_routes,
    )


def setup_v1_docs(app: FastAPI):
    @app.get("/v1/docs", include_in_schema=False)
    async def get_v1_docs():
        return get_swagger_ui_html(
            openapi_url="/v1/openapi.json", title=f"{app.title} - v1"
        )

    @app.get("/v1/re-docs", include_in_schema=False)
    async def get_v1_redoc():
        return get_redoc_html(
            openapi_url="/v1/openapi.json", title=f"{app.title} - v1 (ReDoc)"
        )

    @app.get("/v1/openapi.json", include_in_schema=False)
    async def get_v1_openapi():
        openapi_schema = generate_filtered_openapi(
            app=app, prefix="/api/v1", version="v1", title=f"{app.title} - v1"
        )
        return JSONResponse(openapi_schema)


def setup_base_docs(app: FastAPI):
    @app.get("/docs", include_in_schema=False)
    async def get_docs():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title}")

    @app.get("/re-docs", include_in_schema=False)
    async def get_redoc():
        return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} (ReDoc)")

    @app.get("/openapi.json", include_in_schema=False)
    async def get_base_openapi():
        return JSONResponse(
            get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
        )


def configure_docs(app: FastAPI):
    setup_v1_docs(app)
    setup_base_docs(app)
    return app
