from fastapi import APIRouter, HTTPException

from database import JWTControl, LoginData, UserDB

router = APIRouter()


@router.post("/login")
def login(data: LoginData):
    if not UserDB.check_password(data.username, data.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = JWTControl.create_access(data.username)
    refresh_token = JWTControl.create_refresh(data.username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
