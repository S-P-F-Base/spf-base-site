from fastapi import APIRouter, HTTPException, Request

from data_bases import UserAccess, UserDB
from data_control import ServerControl, req_authorization

router = APIRouter()


@router.get("/status")
def status(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_GAME_SERVER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    status, text = ServerControl.get_status()
    return {"status": status, "text": text}
