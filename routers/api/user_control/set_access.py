from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import AccessData, req_authorization

router = APIRouter()


@router.post("/set_access")
def set_access(request: Request, data: AccessData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_USER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    target = data.target
    access = data.access

    if not UserDB.has_access(username, access):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        UserDB.set_user_access(target, access)

        LogDB.add_log(
            LogType.UPDATE_USER, f"User '{target}' access updated to {access}", username
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200
