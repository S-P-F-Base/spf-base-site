from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import LogRangeData, req_authorization

router = APIRouter()


@router.post("/by_range")
def by_range(request: Request, data: LogRangeData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_range(data.start_id, data.end_id)
