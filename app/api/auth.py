from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.dependencies.db import get_db
from app.schemas.response import Response
from app.schemas.token import Token
from app.services.user import UserService
from app.exceptions import InvalidLogin, InactiveUser

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Response[Token])
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = UserService(db).authenticate(
        username=form_data.username, password=form_data.password
    )

    if not user:
        raise InvalidLogin()
    elif not user.is_active:
        raise InactiveUser()

    user.update(db=db, last_login=datetime.now(timezone.utc))
    toke_data = {"user_id": user.id}

    return Response.success({"access_token": create_access_token(data=toke_data)})
