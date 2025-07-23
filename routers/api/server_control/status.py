from fastapi import APIRouter, HTTPException, Request

from database import (
    ServerControl,
    UserAccess,
    UserDB,
    req_authorization,
)

router = APIRouter()


@router.get("/status")
def status(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(
        username,
        UserAccess.READ_GAME_SERVER.value,
    ):
        raise HTTPException(status_code=403, detail="Insufficient access")

    status, text = ServerControl.get_status()
    return {"status": status, "text": text}
