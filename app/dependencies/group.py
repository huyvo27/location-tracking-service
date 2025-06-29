from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.exceptions import (
    GroupNotFound,
    UserAlreadyMemberOfGroup,
    UserNotMemberOfGroup,
    UserNotOwnerOfGroup,
)
from app.models.group import Group
from app.models.membership import Membership
from app.models.user import User

from .auth import login_required


async def valid_user(user: User = Depends(login_required)) -> User:
    """
    Dependency to checks if the user is already a member of any group.
    """
    if len(user.memberships) > 0:
        raise UserAlreadyMemberOfGroup()
    return user


async def valid_group(group_uuid: str, db: AsyncSession = Depends(get_db)) -> Group:
    """
    Dependency to validate if the group exists.
    """
    group = await Group.find_by(db=db, uuid=group_uuid)
    if not group:
        raise GroupNotFound()
    return group


async def membership_required(
    group: Group = Depends(valid_group),
    user: User = Depends(login_required),
    db: AsyncSession = Depends(get_db),
) -> Group:
    """
    Dependency to ensure the user is a member of the group.
    """
    membership = await Membership.find_by(db=db, user_id=user.id, group_id=group.id)
    if not membership:
        raise UserNotMemberOfGroup()
    return membership


async def ownership_required(
    group: Group = Depends(valid_group),
    user: User = Depends(login_required),
) -> Group:
    """
    Dependency to ensure the user is the owner of the group.
    """
    if group.owner_id != user.id:
        raise UserNotOwnerOfGroup()
    return group
