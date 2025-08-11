from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, PlayerDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


def _parse_delta(
    field: str, current: float, incoming: float | str | None
) -> tuple[float, str | None]:
    if incoming is None:
        return current, None

    op = "set"
    if isinstance(incoming, (int, float)):
        value = float(incoming)
  
    elif isinstance(incoming, str):
        s = incoming.strip().replace(",", ".")
        if not s:
            raise HTTPException(status_code=400, detail=f"{field}: empty string")
      
        sign = s[0]
        if sign in "+-=":
            num = s[1:].strip()
            if not num:
                raise HTTPException(
                    status_code=400,
                    detail=f"{field}: missing numeric part after '{sign}'",
                )
            try:
                val = float(num)
         
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"{field}: invalid number '{num}'"
                )
          
            if sign == "+":
                op = "inc"
                value = current + val
         
            elif sign == "-":
                op = "dec"
                value = current - val
         
            else:
                op = "set"
                value = val
      
        else:
            try:
                value = float(s)
          
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"{field}: invalid number '{s}'"
                )
            op = "set"
   
    else:
        raise HTTPException(status_code=400, detail=f"{field}: unsupported type")

    return value, (f"{field} ({op}): {current} → {value}" if value != current else None)


@router.post("/edit")
def edit_player(
    request: Request,
    u_id: int = Body(...),
    discord_name: str | None = Body(None),
    blacklist: dict[str, bool] | None = Body(None),
    mb_limit: float | str | None = Body(None),
    mb_taken: float | str | None = Body(None),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    entry = PlayerDB.get_pdata_id(u_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Player not found")

    _, discord_id, steam_id, pdata = entry
    changes: list[str] = []

    if discord_name is not None and pdata.discord_name != discord_name:
        changes.append(f"discord_name: '{pdata.discord_name}' → '{discord_name}'")
        pdata.discord_name = discord_name

    if blacklist is not None:
        for key in ("admin", "lore"):
            old_val = bool(pdata.blacklist.get(key))
            new_val = bool(blacklist.get(key))
            if old_val != new_val:
                changes.append(f"blacklist.{key}: {old_val} → {new_val}")
                pdata.blacklist[key] = new_val

    old_limit = float(pdata.mb_limit or 0.0)
    old_taken = float(pdata.mb_taken or 0.0)

    if mb_limit is not None:
        new_limit, log_line = _parse_delta("mb_limit", old_limit, mb_limit)
        if new_limit < 0:
            raise HTTPException(status_code=400, detail="mb_limit must be >= 0")
      
        if log_line:
            changes.append(log_line)
      
        pdata.mb_limit = new_limit

    if mb_taken is not None:
        current_limit = float(pdata.mb_limit or 0.0)
        new_taken, log_line = _parse_delta("mb_taken", old_taken, mb_taken)
        if new_taken < 0:
            raise HTTPException(status_code=400, detail="mb_taken must be >= 0")
        
        if log_line:
            changes.append(log_line)
       
        pdata.mb_taken = new_taken

        if new_taken > current_limit:
            over = new_taken - current_limit
            changes.append(
                f"over-limit: mb_taken({new_taken}) > mb_limit({current_limit}) by {over}"
            )

    if mb_limit is not None and mb_taken is None:
        current_limit = float(pdata.mb_limit or 0.0)
        if old_taken > current_limit:
            over = old_taken - current_limit
            changes.append(
                f"over-limit after limit change: mb_taken({old_taken}) > mb_limit({current_limit}) by {over}"
            )

    PlayerDB.update_player(u_id, discord_id, steam_id, pdata)

    LogDB.add_log(
        LogType.PLAYER_UPDATE,
        f"Player {u_id} edited:\n" + ("\n".join(changes) if changes else "no changes"),
        username,
    )

    return 200
