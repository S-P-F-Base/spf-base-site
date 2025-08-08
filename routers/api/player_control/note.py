from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    NoteData,
    NoteStatus,
    PlayerDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/note/add")
def add_note(
    request: Request,
    u_id: int = Body(...),
    text: str = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    entry = PlayerDB.get_pdata_id(u_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Player not found")

    _, discord_id, steam_id, pdata = entry

    note = NoteData(
        author=username,
        value=text,
        status=NoteStatus.ACTIVE,
        last_status_envoke_author=username,
    )

    pdata.note.append(note)
    PlayerDB.update_player(u_id, discord_id, steam_id, pdata)

    LogDB.add_log(LogType.PLAYER_UPDATE, f"Added note to player {u_id}", username)

    return 200


@router.post("/note/status")
def change_note_status(
    request: Request,
    u_id: int = Body(...),
    index: int = Body(...),
    status: NoteStatus = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    entry = PlayerDB.get_pdata_id(u_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Player not found")

    _, discord_id, steam_id, pdata = entry

    if index < 0 or index >= len(pdata.note):
        raise HTTPException(status_code=400, detail="Invalid note index")

    pdata.note[index].status = status
    pdata.note[index].last_status_envoke_author = username

    PlayerDB.update_player(u_id, discord_id, steam_id, pdata)

    LogDB.add_log(
        LogType.PLAYER_UPDATE, f"Note status changed for player {u_id}", username
    )

    return 200
