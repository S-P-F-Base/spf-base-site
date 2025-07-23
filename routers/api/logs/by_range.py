from fastapi import APIRouter, HTTPException, Request

from database import (
    LogDB,
    LogRangeData,
    UserAccess,
    UserDB,
    req_authorization,
)

router = APIRouter()


@router.post("/by_range")
def by_range(request: Request, data: LogRangeData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS.value):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return LogDB.get_logs_range(data.start_id, data.end_id)