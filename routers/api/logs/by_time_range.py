from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/by_time_range")
def by_time_range(
    request: Request,
    start_time: datetime = Body(...),
    end_time: datetime = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_by_time_range(start_time, end_time)
