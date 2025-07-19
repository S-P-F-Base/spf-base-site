import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from database import JWTControl, UserDB

router = APIRouter()


def clean_username(username: str) -> str:
    return re.sub(r"\s+", " ", username.strip())


@router.post("/register")
def register(form_data: OAuth2PasswordRequestForm = Depends()):
    username = clean_username(form_data.username)
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if UserDB.user_exists(username):
        raise HTTPException(status_code=400, detail="User already exists")

    UserDB.create_user(
        username,
        form_data.password,
        UserDB.system_user,
    )

    access_token = JWTControl.create_access(username)
    refresh_token = JWTControl.create_refresh(username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
