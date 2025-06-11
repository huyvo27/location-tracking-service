from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import (
    login_required,
    permission_required,
    get_current_user,
    get_db,
)
from app.utils.pagination import PaginationParams, paginate
from app.schemas.response import Response, PaginatedResponse
from app.schemas.user import (
    UserItemResponse,
    UserCreateRequest,
    UserUpdateMeRequest,
    UserUpdateRequest,
)
from app.services.user import UserService
from app.models.user import User


router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """
    Dependency to get the UserService instance
    """
    return UserService(db=db)


@router.get(
    "",
    dependencies=[Depends(login_required)],
    response_model=PaginatedResponse[UserItemResponse],
)
def get(params: PaginationParams = Depends(), db: Session = Depends(get_db)) -> Any:
    """
    API Get list User
    """
    _query = db.query(User)
    paginated_users = paginate(query=_query, params=params, schema=UserItemResponse)

    return PaginatedResponse.success(data=paginated_users)


@router.post(
    "",
    dependencies=[permission_required("admin")],
    response_model=Response[UserItemResponse],
)
def create(
    user_data: UserCreateRequest, user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    API Create User
    """
    new_user = user_service.create_user(user_data)
    return Response.success(data=new_user)


@router.get(
    "/me",
    dependencies=[Depends(login_required)],
    response_model=Response[UserItemResponse],
)
def detail_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    API get detail current User
    """
    return Response.success(data=current_user)


@router.put(
    "/me",
    dependencies=[Depends(login_required)],
    response_model=Response[UserItemResponse],
)
def update_me(
    user_data: UserUpdateMeRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """
    API Update current User
    """
    print(user_data)
    updated_user = user_service.update_me(data=user_data, current_user=current_user)
    return Response.success(data=updated_user)


@router.get(
    "/{user_id}",
    dependencies=[Depends(login_required)],
    response_model=Response[UserItemResponse],
)
def detail(user_id: int, user_service: UserService = Depends(get_user_service)) -> Any:
    """
    API get Detail User
    """
    return Response.success(data=user_service.get(user_id))


@router.put(
    "/{user_id}",
    dependencies=[permission_required("admin")],
    response_model=Response[UserItemResponse],
)
def update(
    user_id: int,
    user_data: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """
    API update User
    """
    updated_user = user_service.update(user_id=user_id, data=user_data)
    return Response.success(data=updated_user)


@router.delete(
    "/{user_id}",
    dependencies=[permission_required("admin")],
    response_model=Response[UserItemResponse],
)
def delete(user_id: int, user_service: UserService = Depends(get_user_service)) -> Any:
    """
    API delete User
    """

    user_service.delete(user_id=user_id)
    return Response.success()
