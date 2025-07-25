from fastapi import APIRouter, HTTPException, Request

from data_bases import UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/get_all")
def get_all(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_USER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    data = UserDB.get_all_users()

    return {"logins": data}
