from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.dependencies.auth import get_token_data, login_required
from app.dependencies.db import get_db, get_redis
from app.dependencies.group import (
    ensure_user_is_member_of_group,
    membership_required,
    ownership_required,
    valid_group,
    valid_user,
)
from app.models.group import Group
from app.models.membership import Membership
from app.models.user import User
from app.schemas.group import (
    GroupCreateRequest,
    GroupDetailResponse,
    GroupJoinRequest,
    GroupListRequest,
    GroupUpdateLocationRequest,
    GroupUpdateRequest,
    MembershipResponse,
    SimpleGroupResponse,
    UserLocation,
)
from app.schemas.response import PaginatedResponse, Response
from app.schemas.token import TokenData
from app.services.group import GroupService
from app.services.group_cache import GroupCacheService
from app.utils.pagination import paginate, paginate_without_stmt

router = APIRouter()


async def get_group_service(db: AsyncSession = Depends(get_db)) -> GroupService:
    """
    Dependency to get the GroupService instance
    """
    return GroupService(db=db)


@router.get("", response_model=PaginatedResponse[SimpleGroupResponse])
async def list_group(
    params: GroupListRequest = Depends(),
    user: User = Depends(login_required),
    group_service: GroupService = Depends(get_group_service),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SimpleGroupResponse]:
    """
    Retrieve a paginated list of groups.
    - `joined=true` will return only groups the user belongs to.
    - `only_owned=true` will return only groups owned by the user.
    - If neither is set, returns all groups available.
    """
    if params.joined:
        stmt = await group_service.get_my_groups(user=user, params=params, as_stmt=True)
    else:
        stmt = await group_service.list(params=params, as_stmt=True)

    paginated_groups = await paginate(
        db=db, stmt=stmt, params=params, schema=GroupDetailResponse
    )
    return PaginatedResponse.success(data=paginated_groups)


@router.get(
    "/{group_uuid}",
    dependencies=[Depends(membership_required)],
    response_model=Response[GroupDetailResponse],
    responses={404: {"description": "Group not found"}},
)
async def get_group_detail(
    group: Group = Depends(valid_group),
) -> Response[GroupDetailResponse]:
    """
    Get Group Detail
    """
    return Response.success(data=group)


@router.post(
    "",
    response_model=Response[GroupDetailResponse],
    responses={
        409: {"description": "Group name already exists"},
        400: {"description": "User already a member of a group"},
        422: {"description": "Invalid group data"},
    },
)
async def create(
    group_data: GroupCreateRequest,
    user: User = Depends(valid_user),
    group_service: GroupService = Depends(get_group_service),
) -> Response[GroupDetailResponse]:
    """
    Create a group.
    """
    new_group = await group_service.create_group(data=group_data, user=user)
    try:
        group_cache_service = GroupCacheService(
            redis=await get_redis(str(new_group.uuid)),
            db=None,
            group_uuid=str(new_group.uuid),
        )
        await group_cache_service.add_member(user_uuid=str(user.uuid))
    except Exception as e:
        logger.error(
            f"Failed to add user {user.uuid} to group {new_group.uuid} cache: {e}"
        )
    return Response.success(data=new_group)


@router.post(
    "/{group_uuid}/members",
    response_model=Response[MembershipResponse],
    dependencies=[Depends(valid_user)],
    responses={
        404: {"description": "Group not found"},
        400: {"description": "User already a member of the group"},
    },
)
async def join_group(
    params: GroupJoinRequest,
    group: Group = Depends(valid_group),
    user: User = Depends(valid_user),
    group_service: GroupService = Depends(get_group_service),
) -> Response[MembershipResponse]:
    """
    Join a group. Creates a membership between the user and the group.
    """
    membership = await group_service.join_group(group=group, user=user, params=params)
    try:
        group_cache_service = GroupCacheService(
            redis=await get_redis(str(group.uuid)), db=None, group_uuid=str(group.uuid)
        )
        await group_cache_service.add_member(user_uuid=str(user.uuid))
    except Exception as e:
        logger.error(f"Failed to add user {user.uuid} to group {group.uuid} cache: {e}")
    return Response.success(data=membership)


@router.delete(
    "/{group_uuid}",
    dependencies=[Depends(ownership_required)],
    response_model=Response[None],
    responses={
        404: {"description": "Group not found"},
        403: {"description": "Only the owner can delete the group"},
    },
)
async def delete_group(
    group: Group = Depends(valid_group),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response[None]:
    """
    Delete a group. Only the owner can perform this action.
    """
    try:
        group_cache_service = GroupCacheService(
            redis=redis, db=None, group_uuid=str(group.uuid)
        )
        await group_cache_service.remove_group()
    except Exception as e:
        logger.error(f"Failed to remove group from cache: {e}")
        raise
    await group.delete(db=db)
    return Response.success(data=None)


@router.delete(
    "/{group_uuid}/members/me",
    response_model=Response[None],
    responses={
        404: {"description": "Group not found"},
        403: {"description": "User is not a member of the group"},
    },
)
async def leave_group(
    membership: Membership = Depends(membership_required),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response[None]:
    """
    Allows the current user to leave a group.
    """
    try:
        group_cache_service = GroupCacheService(
            redis=redis,
            db=None,
            group_uuid=str(membership.group_uuid),
        )
        await group_cache_service.remove_member(user_uuid=str(membership.user_uuid))
    except Exception as e:
        logger.error(f"Failed to remove member from cache: {e}")
        raise

    await membership.delete(db=db)
    return Response.success(data=None)


@router.delete(
    "/{group_uuid}/members/{member_uuid}",
    dependencies=[Depends(ownership_required)],
    response_model=Response[None],
    responses={
        404: {"description": "Group or User not found"},
        403: {"description": "Only the owner can kick users from the group"},
    },
)
async def remove_group_member(
    group_uuid: str,
    member_uuid: str,
    group: Group = Depends(valid_group),
    group_service: GroupService = Depends(get_group_service),
    redis: Redis = Depends(get_redis),
) -> Response[None]:
    """
    API Kick User from Group
    """
    try:
        group_cache_service = GroupCacheService(
            redis=redis, db=None, group_uuid=group_uuid
        )
        await group_cache_service.remove_member(user_uuid=member_uuid)
    except Exception as e:
        logger.error(f"Failed to remove member from cache: {e}")
        raise

    await group_service.kick_member(group=group, member_uuid=member_uuid)
    return Response.success(data=None)


@router.put(
    "/{group_uuid}",
    dependencies=[Depends(ownership_required)],
    response_model=Response[GroupDetailResponse],
    responses={
        404: {"description": "Group not found"},
        422: {"description": "Invalid group data"},
        403: {"description": "Only the owner can update the group"},
    },
)
async def update_group(
    group_data: GroupUpdateRequest,
    group: Group = Depends(valid_group),
    group_service: GroupService = Depends(get_group_service),
) -> Response[GroupDetailResponse]:
    """
    Update group information. Only the group owner can perform this action.
    """
    updated_group = await group_service.update_group(group=group, data=group_data)
    return Response.success(data=updated_group)


@router.put("/{group_uuid}/members/me/location")
async def update_my_location(
    location: GroupUpdateLocationRequest,
    group_cache_service: GroupCacheService = Depends(ensure_user_is_member_of_group),
    token_data: TokenData = Depends(get_token_data),
) -> Response[None]:
    """
    Update the current user's location in a group.
    """
    await group_cache_service.update_location(token_data.sub, location)
    return Response.success()


@router.get("/{group_uuid}/members/locations")
async def get_locations(
    group_cache_service: GroupCacheService = Depends(ensure_user_is_member_of_group),
) -> PaginatedResponse[UserLocation]:
    """
    Get locations of members in a group.
    """
    group_locations = await group_cache_service.get_group_locations()
    paginated_data = paginate_without_stmt(items=group_locations, schema=UserLocation)
    return Response.success(data=paginated_data)
