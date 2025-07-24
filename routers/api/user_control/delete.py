from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import TargetUserData, req_authorization

router = APIRouter()


@router.post("/delete")
def delete(request: Request, data: TargetUserData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_USER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    target = data.target

    try:
        UserDB.delete_user(target)

        LogDB.add_log(LogType.DELETE_USER, f"Deleted user {target}", username)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200
