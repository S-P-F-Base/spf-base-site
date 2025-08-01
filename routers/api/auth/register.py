import re

from fastapi import APIRouter, HTTPException

from data_bases import LogDB, LogType, UserDB
from data_control import JWTControl, LoginAPIData

router = APIRouter()


def clean_username(username: str) -> str:
    return re.sub(r"\s+", "_", username.strip())


@router.post("/register")
def register(data: LoginAPIData):
    if not data.username.isascii():
        raise HTTPException(status_code=400, detail="Username contain non-ascii")

    username = clean_username(data.username)
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if UserDB.user_exists(username):
        raise HTTPException(status_code=400, detail="User already exists")

    UserDB.create_user(username, data.password)
    LogDB.add_log(LogType.USER_CREATE, f"Created user {username}", UserDB.system_user)

    access_token = JWTControl.create_access(username)
    refresh_token = JWTControl.create_refresh(username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
