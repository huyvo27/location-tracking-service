from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.dependencies.auth import (
    get_current_user,
    login_required,
    permission_required,
)
from app.models.user import User
from app.schemas.response import PaginatedResponse, Response
from app.schemas.user import (
    UserCreateRequest,
    UserLimitedResponse,
    UserListRequest,
    UserResponse,
    UserUpdateMeRequest,
    UserUpdateRequest,
)
from app.services.user import UserService
from app.utils.enums import UserRole
from app.utils.pagination import paginate

router = APIRouter()


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Dependency to get the UserService instance
    """
    return UserService(db=db)


@router.get("")
async def list(
    params: UserListRequest = Depends(),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(login_required),
) -> Any:
    """
    API Get list User
    """
    stmt = await user_service.list(params=params, as_stmt=True)

    schema = (
        UserResponse
        if current_user.role == UserRole.SYS_ADMIN.value
        else UserLimitedResponse
    )

    paginated_users = await paginate(db=db, stmt=stmt, params=params, schema=schema)

    return PaginatedResponse.success(data=paginated_users)


@router.post(
    "",
    dependencies=[permission_required(UserRole.SYS_ADMIN.value)],
    response_model=Response[UserResponse],
)
async def create(
    user_data: UserCreateRequest, user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    API Create User
    """
    new_user = await user_service.create_user(user_data)
    return Response.success(data=new_user)


@router.get(
    "/me",
    dependencies=[Depends(login_required)],
    response_model=Response[UserResponse],
)
async def detail_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    API get detail current User
    """
    return Response.success(data=current_user)


@router.put(
    "/me",
    dependencies=[Depends(login_required)],
    response_model=Response[UserResponse],
)
async def update_me(
    user_data: UserUpdateMeRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """
    API Update current User
    """
    updated_user = await user_service.update_me(
        data=user_data, current_user=current_user
    )
    return Response.success(data=updated_user)


@router.get("/{user_uuid}")
async def detail(
    user_uuid: str, user_service: UserService = Depends(get_user_service), current_user: User = Depends(login_required)
) -> Any:
    """
    API get Detail User
    """
    user = await user_service.get(user_uuid)
    schema = (
        UserResponse
        if current_user.role == UserRole.SYS_ADMIN.value
        else UserLimitedResponse
    )
    return Response[schema].success(data=user)


@router.put(
    "/{user_uuid}",
    dependencies=[permission_required(UserRole.SYS_ADMIN.value)],
    response_model=Response[UserResponse],
)
async def update(
    user_uuid: str,
    user_data: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """
    API update User
    """
    updated_user = await user_service.update(user_uuid=user_uuid, data=user_data)
    return Response.success(data=updated_user)


@router.delete(
    "/{user_uuid}",
    dependencies=[permission_required(UserRole.SYS_ADMIN.value)],
    response_model=Response[UserResponse],
)
async def delete(
    user_uuid: str, user_service: UserService = Depends(get_user_service)
) -> Any:
    """
    API delete User
    """
    await user_service.delete(user_uuid=user_uuid)
    return Response.success()
