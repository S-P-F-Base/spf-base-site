from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, PlayerDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/edit")
def edit_player(
    request: Request,
    u_id: int = Body(...),
    discord_name: str | None = Body(None),
    discord_avatar: str | None = Body(None),
    blacklist: dict[str, bool] | None = Body(None),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    entry = PlayerDB.get_pdata_id(u_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Player not found")

    _, discord_id, steam_id, pdata = entry

    changes = []

    if discord_name is not None and pdata.discord_name != discord_name:
        changes.append(f"discord_name: '{pdata.discord_name}' → '{discord_name}'")
        pdata.discord_name = discord_name

    if discord_avatar is not None and pdata.discord_avatar != discord_avatar:
        changes.append(f"discord_avatar: '{pdata.discord_avatar}' → '{discord_avatar}'")
        pdata.discord_avatar = discord_avatar

    if blacklist is not None:
        for key in ("admin", "lore"):
            old_val = pdata.blacklist.get(key)
            new_val = bool(blacklist.get(key))
            if old_val != new_val:
                changes.append(f"blacklist.{key}: {old_val} → {new_val}")
                pdata.blacklist[key] = new_val

    PlayerDB.update_player(u_id, discord_id, steam_id, pdata)

    if changes:
        log_msg = f"Player {u_id} edited:\n" + "\n".join(changes)
    else:
        log_msg = f"Player {u_id} edit attempted with no changes"

    LogDB.add_log(LogType.PLAYER_UPDATE, log_msg, username)

    return 200
