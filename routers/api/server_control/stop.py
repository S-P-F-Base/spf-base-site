from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import ServerControl, req_authorization

router = APIRouter()


@router.get("/stop")
def stop(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_GAME_SERVER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    ServerControl.perform_action("stop")
    LogDB.add_log(LogType.GAME_SERVER_STOP, "The server has stopped", username)
    return 200
