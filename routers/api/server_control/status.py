from fastapi import APIRouter, HTTPException, Request

from data_bases import UserAccess, UserDB
from data_control import ServerControl, WebSocketManager, req_authorization

router = APIRouter()


@router.get("/status")
def statuse(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_GAME_SERVER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    return {"status": ServerControl.get_status()}


@router.get("/status/subscribe")
def status_subscribe(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_GAME_SERVER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    WebSocketManager.subscribe(username, "server_control_status")

    return 200


@router.get("/status/unsubscribe")
def status_unsubscribe(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_GAME_SERVER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    WebSocketManager.unsubscribe(username, "server_control_status")

    return 200
