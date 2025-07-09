from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from database import JWTControl, UserDB

router = APIRouter()


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not UserDB.check_password(form_data.username, form_data.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = JWTControl.create_access(form_data.username)
    refresh_token = JWTControl.create_refresh(form_data.username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
