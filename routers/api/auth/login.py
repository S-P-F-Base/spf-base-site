from fastapi import APIRouter, Body, HTTPException

from data_bases import UserDB
from data_control import JWTControl

router = APIRouter()


@router.post("/login")
def login(
    username: str = Body(...),
    password: str = Body(...),
):
    if not UserDB.check_password(username, password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = JWTControl.create_access(username)
    refresh_token = JWTControl.create_refresh(username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
