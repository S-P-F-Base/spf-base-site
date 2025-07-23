from fastapi import APIRouter, HTTPException, Request

from database import TargetUserData, UserAccess, UserDB, req_authorization

router = APIRouter()


@router.post("/delete")
def delete(request: Request, data: TargetUserData):
    username = req_authorization(request)
    if not UserDB.has_access(
        username,
        UserAccess.CONTROL_USER.value,
    ):
        raise HTTPException(status_code=403, detail="Insufficient access")

    target = data.target

    try:
        UserDB.delete_user(target, username)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    return 200