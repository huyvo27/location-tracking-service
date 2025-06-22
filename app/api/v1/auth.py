from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.dependencies.db import get_db
from app.exceptions import InactiveUser, InvalidLogin
from app.schemas.response import Response
from app.schemas.token import Token
from app.services.user import UserService

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Response[Token])
async def login(form_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await UserService(db).authenticate(
        username=form_data.username, password=form_data.password
    )
    """
    API Login User
    Authenticate user with username and password, and return an access token.
    """

    if not user:
        raise InvalidLogin()
    elif not user.is_active:
        raise InactiveUser()

    await user.update(db=db, last_login=datetime.now(timezone.utc))
    toke_data = {"sub": user.uuid_str}

    return Response.success({"access_token": create_access_token(data=toke_data)})
