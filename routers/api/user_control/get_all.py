from fastapi import APIRouter, HTTPException, Request

from database import UserAccess, UserDB, req_authorization

router = APIRouter()


@router.get("/get_all")
def get_all(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_USER.value):
        raise HTTPException(status_code=403, detail="Insufficient access")

    data = UserDB.get_all_users()

    return {"logins": data}
