from fastapi import APIRouter, HTTPException, Request

from database import (
    LogDB,
    LogType,
    ServerControl,
    UserAccess,
    UserDB,
    req_authorization,
)

router = APIRouter()


@router.get("/start")
def start(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(
        username,
        UserAccess.CONTROL_GAME_SERVER.value,
    ):
        raise HTTPException(status_code=403, detail="Insufficient access")

    ServerControl.perform_action("start")
    LogDB.add_log(LogType.GAME_SERVER_START, "The server has started", username)
    return 200
