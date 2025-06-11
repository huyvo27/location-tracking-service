from typing import Optional
from fastapi_sqlalchemy import db
from sqlalchemy import or_, orm

from app.models.user import User
from app.core.security import verify_password, hash_password
from app.schemas.user import UserCreateRequest, UserUpdateMeRequest, UserUpdateRequest
from app.exceptions import UserNotFound, UsernameEmailAlreadyExists


class UserService:
    def __init__(self, db: orm.Session) -> None:
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = (
            self.db.query(User)
            .filter(or_(User.email == username, User.username == username))
            .first()
        )
        if user and verify_password(password, user.hashed_password):
            return user
        return None

    def create_user(self, data: UserCreateRequest):
        exist_user = (
            self.db.query(User)
            .filter(or_(User.email == data.email, User.username == data.username))
            .first()
        )
        if exist_user:
            raise UsernameEmailAlreadyExists()

        new_user = User.create(
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

    def update_me(self, data: UserUpdateMeRequest, current_user: User):

        return current_user.update(
            db=self.db,
            full_name=data.full_name,
            phone_number=data.phone_number,
            email=data.email,
            hashed_password=hash_password(data.password) if data.password else None,
        )

    def update(self, user_id: int, data: UserUpdateRequest):
        user = self.get(user_id)

        return user.update(
            db=self.db,
            full_name=data.full_name,
            phone_number=data.phone_number,
            email=data.email,
            hashed_password=hash_password(data.password) if data.password else None,
            is_active=data.is_active,
            role=user.role if data.role is None else data.role.value,
        )

    def get(self, user_id):
        exist_user = User.find(db=self.db, _id=user_id)
        if exist_user is None:
            raise UserNotFound()
        return exist_user

    def delete(self, user_id):
        user = self.get(user_id)
        if user:
            user.delete(db=self.db)
            return True
        return False
