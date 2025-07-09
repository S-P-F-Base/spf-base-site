from fastapi import APIRouter, Request

from database import JWTControl, req_refresh

router = APIRouter()


@router.post("/refresh")
def refresh(request: Request):
    username = req_refresh(request)

    access_token = JWTControl.create_access(username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
