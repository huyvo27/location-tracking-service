from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.exceptions.base import CustomAPIException
from app.schemas.response import Response

from .logger import logger


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
        try:
            msg = exc.errors()[0].get("msg", "Invalid input")
        except IndexError:
            msg = "Invalid input"

        response = Response.error(
            code="422", message= f"Validation Error: {msg}"
        )
        # logger.info(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(response, exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        response = Response.error(code="500", message="Internal Server Error")
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(response, exclude_none=True),
        )

    @app.exception_handler(CustomAPIException)
    async def custom_handler(request: Request, exc: CustomAPIException):
        response = Response.error(code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.http_code,
            content=jsonable_encoder(response, exclude_none=True),
        )
