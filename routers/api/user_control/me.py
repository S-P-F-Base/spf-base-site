from fastapi import APIRouter, HTTPException, Request

from data_bases import UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/me")
def me(request: Request):
    username = req_authorization(request)

    access = UserDB.get_user_access(username)
    if access is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"login": username, "access": access}
