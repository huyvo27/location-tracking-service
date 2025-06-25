from typing import Generic, Optional, TypeVar

from app.utils.pagination import PaginatedData

from .base import BaseSchema

T = TypeVar("T")


class Response(BaseSchema, Generic[T]):
    """
    Example usage:
        class UserSchema(BaseModel):
            id: int
            name: str

        Response[UserSchema].success(data=user)
        Response[UserSchema].error(code='001', message='User not found')
    """

    code: str
    message: str
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Optional[T] = None):
        return cls(code="000", message="Success", data=data)

    @classmethod
    def error(cls, code: str, message: str):
        return cls(code=code, message=message)


class PaginatedResponse(Response[PaginatedData[T]]):
    """
    Example usage:
        class UserSchema(BaseModel):
            id: int
            name: str

        PaginatedResponse[UserSchema].success(data=PaginatedData(items=[user], metadata=metadata))
    """

    pass
