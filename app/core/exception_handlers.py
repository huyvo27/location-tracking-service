from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
)
from app.exceptions.base import CustomAPIException
from app.schemas.response import Response


def register_exception_handlers(app):
    """
    Register exception handlers for the FastAPI application.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        response = Response.error(code=str(exc.status_code), message=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(response, exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        response = Response.error(code="422", message="Validation Error")
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(response, exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        response = Response.error(code="500", message=str(exc))
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(response, exclude_none=True),
        )

    @app.exception_handler(CustomAPIException)
    async def custom_handler(request, exc: CustomAPIException):
        response = Response.error(code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.http_code,
            content=jsonable_encoder(response, exclude_none=True),
        )
