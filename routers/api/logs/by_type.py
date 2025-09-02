from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/by_type")
def by_type(
    request: Request,
    log_type: int = Body(..., embed=True),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        enum_type = LogType(log_type)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log type")

    return LogDB.get_logs_by_type(enum_type)
