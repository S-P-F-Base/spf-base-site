from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import req_authorization

from .base_func import load_data, save_data

router = APIRouter()


@router.post("/delete")
def delete_character(
    request: Request,
    key: str = Body(..., embed=True),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.LORE_CHAR_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    characters = load_data()
    if key not in characters:
        raise HTTPException(status_code=404, detail="Character not found")

    del characters[key]
    save_data(characters)

    LogDB.add_log(LogType.LORE_CHAR_DELETE, f"Lore char deleted {key}", username)
    return {"success": True}
