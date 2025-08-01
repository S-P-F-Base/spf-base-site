from fastapi import APIRouter, Request

from data_control import JWTControl, req_refresh

router = APIRouter()


@router.get("/refresh")
def refresh(request: Request):
    username = req_refresh(request)

    access_token = JWTControl.create_access(username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
