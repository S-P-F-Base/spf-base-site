from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import LogTypeData, req_authorization

router = APIRouter()


@router.post("/by_type")
def by_type(request: Request, data: LogTypeData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        log_type = LogType(data.log_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log type")

    return LogDB.get_logs_by_type(log_type)
