from fastapi import APIRouter, HTTPException, Request

from data_bases import UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/tea_pot")
def tea_pot(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.ALL_ACCESS):
        raise HTTPException(status_code=403, detail="Insufficient access")

    with open("TEAPOT", "w"):
        pass

    return {"status": "The server turned into a teapot"}
