from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/min_max_id")
def min_max_id(
    request: Request,
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_LOGS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    start_id, end_id = LogDB.get_min_max_log_id()

    return {"start_id": start_id, "end_id": end_id}
