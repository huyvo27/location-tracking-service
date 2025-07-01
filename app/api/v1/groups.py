from fastapi import APIRouter, BackgroundTasks, Depends
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
    KickMemberRequest,
    MembershipResponse,
    MyGroupListRequest,
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


@router.get(
    "",
    response_model=PaginatedResponse[SimpleGroupResponse],
    dependencies=[Depends(login_required)],
)
async def list(
    params: GroupListRequest = Depends(),
    group_service: GroupService = Depends(get_group_service),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SimpleGroupResponse]:
    """
    API Get list all Groups
    """
    stmt = await group_service.list(params=params, as_stmt=True)

    paginated_groups = await paginate(
        db=db, stmt=stmt, params=params, schema=GroupDetailResponse
    )
    return PaginatedResponse.success(data=paginated_groups)


@router.get(
    "/me",
    response_model=PaginatedResponse[SimpleGroupResponse],
    dependencies=[Depends(login_required)],
)
async def get_my_groups(
    params: MyGroupListRequest = Depends(),
    user: User = Depends(login_required),
    group_service: GroupService = Depends(get_group_service),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SimpleGroupResponse]:
    """
    API Get list Groups that the user belongs to
    """
    stmt = await group_service.get_my_groups(user=user, params=params, as_stmt=True)

    paginated_groups = await paginate(
        db=db, stmt=stmt, params=params, schema=SimpleGroupResponse
    )
    return PaginatedResponse.success(data=paginated_groups)


@router.get(
    "/{group_uuid}",
    dependencies=[Depends(membership_required)],
    response_model=Response[GroupDetailResponse],
    responses={404: {"description": "Group not found"}},
)
async def detail(group: Group = Depends(valid_group)) -> Response[GroupDetailResponse]:
    """
    API Get Group Detail
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
    API Create Group
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
    "/{group_uuid}/join",
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
    API Join Group
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
async def delete(
    group: Group = Depends(valid_group),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Response[None]:
    """
    API Delete Group
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
    "/{group_uuid}/leave",
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
    API Leave Group
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
    "/{group_uuid}/kick/{member_uuid}",
    dependencies=[Depends(ownership_required)],
    response_model=Response[None],
    responses={
        404: {"description": "Group or User not found"},
        403: {"description": "Only the owner can kick users from the group"},
    },
)
async def kick_user(
    params: KickMemberRequest = Depends(),
    group: Group = Depends(valid_group),
    group_service: GroupService = Depends(get_group_service),
    redis: Redis = Depends(get_redis),
) -> Response[None]:
    """
    API Kick User from Group
    """
    try:
        group_cache_service = GroupCacheService(
            redis=redis, db=None, group_uuid=str(group.uuid)
        )
        await group_cache_service.remove_member(user_uuid=str(params.member_uuid))
    except Exception as e:
        logger.error(f"Failed to remove member from cache: {e}")
        raise

    await group_service.kick_member(group=group, member_uuid=params.member_uuid)
    return Response.success(data=None)


@router.put(
    "/{group_uuid}/update",
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
    API Update Group
    """
    updated_group = await group_service.update_group(group=group, data=group_data)
    return Response.success(data=updated_group)


@router.put("/{group_uuid}/locations")
async def update_location(
    location: GroupUpdateLocationRequest,
    group_cache_service: GroupCacheService = Depends(ensure_user_is_member_of_group),
    token_data: TokenData = Depends(get_token_data),
) -> Response[None]:
    """
    API Update member's location
    """
    await group_cache_service.update_location(token_data.sub, location)
    return Response.success()


@router.get("/{group_uuid}/locations")
async def get_locations(
    group_cache_service: GroupCacheService = Depends(ensure_user_is_member_of_group),
) -> PaginatedResponse[UserLocation]:
    """
    API Get all locations in group
    """
    group_locations = await group_cache_service.get_group_locations()
    paginated_data = paginate_without_stmt(items=group_locations, schema=UserLocation)
    return Response.success(data=paginated_data)
