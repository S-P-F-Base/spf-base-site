from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/by_creator")
def by_creator(
    request: Request,
    target: str = Body(..., embed=True),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_by_creator(target)
