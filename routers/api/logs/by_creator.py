from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import TargetUserData, req_authorization

router = APIRouter()


@router.post("/by_creator")
def by_creator(request: Request, data: TargetUserData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_by_creator(data.target)
