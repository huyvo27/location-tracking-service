from typing import Optional, TypeVar, Generic
from pydantic import BaseModel

from app.utils.pagination import PaginatedData

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
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
    pass


# Example usage
# class UserSchema(BaseModel):
#     id: int
#     name: str
#
# Response[UserSchema].success(data=user)
# Response[UserSchema].error(code='001', message='User not found')
#
# PaginatedResponse[UserSchema].success(data=PaginatedData(items=[user], metadata=metadata))
