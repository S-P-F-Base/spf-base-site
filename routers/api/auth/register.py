import re

from fastapi import APIRouter, HTTPException

from database import JWTControl, LoginData, UserDB

router = APIRouter()


def clean_username(username: str) -> str:
    return re.sub(r"\s+", " ", username.strip())


@router.post("/register")
def register(data: LoginData):
    username = clean_username(data.username)
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if UserDB.user_exists(username):
        raise HTTPException(status_code=400, detail="User already exists")

    UserDB.create_user(
        username,
        data.password,
        UserDB.system_user,
    )

    access_token = JWTControl.create_access(username)
    refresh_token = JWTControl.create_refresh(username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
