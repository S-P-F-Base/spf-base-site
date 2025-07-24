from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import LogTimeRangeData, req_authorization

router = APIRouter()


@router.post("/by_time_range")
def by_time_range(request: Request, data: LogTimeRangeData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_by_time_range(data.start_time, data.end_time)
