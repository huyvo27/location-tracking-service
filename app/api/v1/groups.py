from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import login_required
from app.dependencies.db import get_db
from app.dependencies.group import (
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
    GroupUpdateRequest,
    KickMemberRequest,
    MembershipResponse,
    MyGroupListRequest,
    SimpleGroupResponse,
)
from app.schemas.response import PaginatedResponse, Response
from app.services.group import GroupService
from app.utils.pagination import paginate

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
    group: Group = Depends(valid_group), db: AsyncSession = Depends(get_db)
) -> Response[None]:
    """
    API Delete Group
    """
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
) -> Response[None]:
    """
    API Leave Group
    """
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
) -> Response[None]:
    """
    API Kick User from Group
    """
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
