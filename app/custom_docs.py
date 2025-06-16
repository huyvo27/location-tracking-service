from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI):
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = openapi
    return app


def setup_v1_docs(app: FastAPI):
    @app.get("/v1/docs", include_in_schema=False)
    async def get_v1_docs():
        return get_swagger_ui_html(
            openapi_url="/v1/openapi.json", title=f"{app.title} - v1"
        )

    @app.get("/v1/openapi.json", include_in_schema=False)
    async def get_v1_openapi():
        return app.openapi()

    @app.get("/v1/re-docs", include_in_schema=False)
    async def get_v1_redoc():
        return get_redoc_html(
            openapi_url="/v1/openapi.json", title=f"{app.title} - v1 (ReDoc)"
        )


def configure_docs(app: FastAPI):
    app = custom_openapi(app)
    setup_v1_docs(app)
    return app
