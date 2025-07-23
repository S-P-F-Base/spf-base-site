from fastapi import APIRouter, HTTPException, Request

from database import AccessData, UserAccess, UserDB, req_authorization

router = APIRouter()


@router.post("/set_access")
def set_access(request: Request, data: AccessData):
    username = req_authorization(request)
    if not UserDB.has_access(
        username,
        UserAccess.CONTROL_USER.value,
    ):
        raise HTTPException(status_code=403, detail="Insufficient access")

    target = data.target
    access = data.access

    if not UserDB.has_access(username, access):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        UserDB.set_user_access(target, access, username)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200
