from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/delete")
def delete(
    request: Request,
    target: str = Body(..., embed=True),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_USER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        UserDB.delete_user(target)
        LogDB.add_log(LogType.USER_DELETE, f"Deleted user {target}", username)

    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200
