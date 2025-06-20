from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import verify_password, hash_password
from app.schemas.user import UserCreateRequest, UserUpdateMeRequest, UserUpdateRequest
from app.exceptions import UserNotFound, UsernameEmailAlreadyExists


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        stmt = select(User).where(
            or_(User.email == username, User.username == username)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user and verify_password(password, user.hashed_password):
            return user
        return None

    async def create_user(self, data: UserCreateRequest):
        stmt = select(User).where(or_(User.email == data.email, User.username == data.username))
        result = await self.db.execute(stmt)
        exist_user = result.scalars().first()

        if exist_user:
            raise UsernameEmailAlreadyExists()

        new_user = await User.create(
            db=self.db,
            username=data.username,
            phone_number=data.phone_number,
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
            is_active=data.is_active,
            role=data.role.value,
        )

        return new_user

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

    async def delete(self, user_uuid: str):
        user = await self.get(user_uuid)
        if user:
            await user.delete(db=self.db)
            return True
        return False
