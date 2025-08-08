from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import LoreCharCreateAPIData, req_authorization

from .base_func import load_data, save_data

router = APIRouter()


@router.post("/create")
def create_character(request: Request, data: LoreCharCreateAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.LORE_CHAR_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    characters = load_data()
    if data.key in characters:
        raise HTTPException(status_code=409, detail="Character already exists")

    characters[data.key] = {
        "name": data.name,
        "status": data.status,
        "wiki": data.wiki or "",
    }
    save_data(characters)

    LogDB.add_log(LogType.LORE_CHAR_CREATE, f"Created lore char {data.key}", username)
    return {"success": True}
