from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/set_access")
def set_access(
    request: Request,
    target: str = Body(...),
    access: int = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_USER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    if not UserDB.has_access(username, access):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        UserDB.set_user_access(target, access)
        LogDB.add_log(
            LogType.USER_UPDATE, f"User '{target}' access updated to {access}", username
        )

    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200
