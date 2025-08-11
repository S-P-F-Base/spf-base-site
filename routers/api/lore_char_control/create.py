from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import req_authorization

from .base_func import load_data, save_data

router = APIRouter()


@router.post("/create")
def create_character(
    request: Request,
    key: str = Body(...),
    name: str = Body(...),
    status: Literal["free", "taken", "blocked"] = Body(...),
    wiki: str | None = Body(None),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.LORE_CHAR_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    characters = load_data()
    if key in characters:
        raise HTTPException(status_code=409, detail="Character already exists")

    characters[key] = {
        "name": name,
        "status": status,
        "wiki": wiki or "",
    }
    save_data(characters)

    LogDB.add_log(LogType.LORE_CHAR_CREATE, f"Created lore char {key}", username)
    return {"success": True}
