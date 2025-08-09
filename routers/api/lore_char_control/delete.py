from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import LoreCharKeyAPIData, req_authorization

from .base_func import load_data, save_data

router = APIRouter()


@router.post("/delete")
def delete_character(request: Request, data: LoreCharKeyAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.LORE_CHAR_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    characters = load_data()
    if data.key not in characters:
        raise HTTPException(status_code=404, detail="Character not found")

    del characters[data.key]
    save_data(characters)

    LogDB.add_log(LogType.LORE_CHAR_DELETE, f"Lore char deleted {data.key}", username)
    return {"success": True}
