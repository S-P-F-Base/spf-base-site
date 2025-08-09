from fastapi import APIRouter, HTTPException, Request

from data_bases import UserAccess, UserDB
from data_control import TargetUserAPIData, req_authorization

router = APIRouter()


@router.post("/get_info")
def get_info(request: Request, data: TargetUserAPIData):
    username = req_authorization(request)

    target = data.target

    if not (username == target or UserDB.has_access(username, UserAccess.READ_USER)):
        raise HTTPException(status_code=403, detail="Insufficient access")

    access = UserDB.get_user_access(target)
    if access is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"login": target, "access": access}
