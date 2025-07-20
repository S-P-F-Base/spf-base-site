from fastapi import APIRouter, HTTPException, Request

from database import TargetUserData, UserAccess, UserDB, req_authorization

router = APIRouter()


@router.post("/get_info")
def get_info(request: Request, data: TargetUserData):
    username = req_authorization(request)

    target = data.target

    if not (
        username == target
        or UserDB.has_access(
            username,
            UserAccess.READ_USER_DATA.value,
        )
    ):
        raise HTTPException(status_code=403, detail="Insufficient access")

    access = UserDB.get_user_access(target)
    if access is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"login": target, "access": access}
