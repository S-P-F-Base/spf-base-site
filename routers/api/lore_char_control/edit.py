from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, UserAccess, UserDB
from data_control import LoreCharEditAPIData, req_authorization

from .base_func import load_data, save_data

router = APIRouter()


@router.post("/edit")
def edit_character(request: Request, data: LoreCharEditAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.LORE_CHAR_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    characters = load_data()
    if data.key not in characters:
        raise HTTPException(status_code=404, detail="Character not found")

    prev = characters[data.key]
    characters[data.key] = {
        "name": data.name,
        "status": data.status,
        "wiki": data.wiki or "",
    }
    save_data(characters)

    LogDB.add_log(
        LogType.LORE_CHAR_EDIT,
        f"Lore char edited {data.key}: "
        f"'{prev['name']}'({prev['status']}) → '{data.name}'({data.status})",
        username,
    )
    return {"success": True}
