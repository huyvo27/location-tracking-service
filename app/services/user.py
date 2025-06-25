from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.exceptions import (
    InactiveUser,
    InvalidLogin,
    UsernameEmailAlreadyExists,
    UserNotFound,
)
from app.models.user import User
from app.schemas.user import (
    UserCreateRequest,
    UserListRequest,
    UserRegisterRequest,
    UserUpdateMeRequest,
    UserUpdateRequest,
)
from app.utils.enums import UserRole


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        user = await User.find_by(
            db=self.db, username=username, email=username, use_or=True
        )

        if not user or not verify_password(password, user.hashed_password):
            raise InvalidLogin()

        if not user.is_active:
            raise InactiveUser()

        return user

    async def create_user(self, data: UserCreateRequest):
        exist_user = await User.find_by(
            db=self.db, username=data.username, email=data.email, use_or=True
        )

        if exist_user:
            raise UsernameEmailAlreadyExists()

        is_active = data.is_active if hasattr(data, "is_active") else True
        role = data.role if hasattr(data, "role") else UserRole.USER

        new_user = await User.create(
            db=self.db,
            username=data.username,
            phone_number=data.phone_number,
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
            is_active=is_active,
            role=role.value,
        )

        return new_user

    async def register_user(self, data: UserRegisterRequest):
        return await self.create_user(data)

    async def update_me(self, data: UserUpdateMeRequest, current_user: User):
        return await current_user.update(
            db=self.db,
            full_name=data.full_name,
            phone_number=data.phone_number,
            email=data.email,
            hashed_password=hash_password(data.password) if data.password else None,
        )

    async def update(self, user_uuid: int, data: UserUpdateRequest):
        user = await self.get(user_uuid)

        return await user.update(
            db=self.db,
            full_name=data.full_name,
            phone_number=data.phone_number,
            email=data.email,
            hashed_password=hash_password(data.password) if data.password else None,
            is_active=data.is_active,
            role=user.role if data.role is None else data.role.value,
        )

    async def get(self, user_uuid: str) -> User:
        exist_user = await User.find_by(db=self.db, uuid=user_uuid)
        if exist_user is None:
            raise UserNotFound()
        return exist_user

    async def list(self, params: UserListRequest, as_stmt: bool = False):
        contains = {}
        if params.search:
            contains["full_name"] = params.search
            contains["username"] = params.search
            contains["email"] = params.search

        return await User.filter_by(db=self.db, contains=contains, as_stmt=as_stmt)

    async def delete(self, user_uuid: str) -> bool:
        try:
            user = await self.get(user_uuid)
            await user.delete(db=self.db)
            return True
        except UserNotFound:
            return False
