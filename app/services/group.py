from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.exceptions import (
    GroupNameAlreadyExists,
    InvalidGroupKey,
    UserNotFound,
    UserNotFoundInGroup,
)
from app.models.group import Group
from app.models.membership import Membership
from app.models.user import User
from app.schemas.group import (
    GroupCreateRequest,
    GroupJoinRequest,
    GroupListRequest,
    GroupUpdateRequest,
    MyGroupListRequest,
)


class GroupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_group(self, data: GroupCreateRequest, user: User) -> Group:
        existing_group = await Group.find_by(db=self.db, name=data.name)

        if existing_group:
            raise GroupNameAlreadyExists()

        new_group = await Group.create(
            db=self.db,
            name=data.name,
            description=data.description,
            hashed_key=hash_password(data.key),
            owner_id=user.id,
        )
        await Membership.add_membership(
            db=self.db, user_id=user.id, group_id=new_group.id
        )

        return new_group

    async def join_group(
        self, group: Group, user: User, params: GroupJoinRequest
    ) -> Membership:
        if not verify_password(params.key, group.hashed_key):
            raise InvalidGroupKey()

        membership = await Membership.add_membership(
            db=self.db, user_id=user.id, group_id=group.id
        )
        group.member_count += 1
        await group.save(db=self.db)

        return membership

    async def list(self, params: GroupListRequest, as_stmt: bool = False):
        contains = {}
        if params.search:
            contains["name"] = params.search

        return await Group.filter_by(db=self.db, contains=contains, as_stmt=as_stmt)

    async def get_my_groups(
        self, user: User, params: MyGroupListRequest, as_stmt: bool = False
    ):
        contains = {}
        if params.search:
            contains["name"] = params.search

        if params.only_owned:
            return await Group.filter_by(
                db=self.db, owner_id=user.id, contains=contains, as_stmt=as_stmt
            )

        memberships = await Membership.filter_by(db=self.db, user_id=user.id)
        group_ids = [membership.group_id for membership in memberships]
        return await Group.filter_by(
            db=self.db, id__in=group_ids, contains=contains, as_stmt=as_stmt
        )

    async def kick_member(self, group: Group, member_uuid: UUID) -> None:
        member = await User.find_by(db=self.db, uuid=member_uuid)
        if not member:
            raise UserNotFound()

        membership = await Membership.find_by(
            db=self.db, user_id=member.id, group_id=group.id
        )

        if not membership:
            raise UserNotFoundInGroup()

        await membership.delete(db=self.db)

    async def update_group(self, group: Group, data: GroupUpdateRequest) -> Group:
        if data.description is not None:
            group.description = data.description
        if data.capacity is not None:
            group.capacity = data.capacity
        if data.key is not None:
            group.hashed_key = hash_password(data.key)

        await group.save(db=self.db)

        return group
