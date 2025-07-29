from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from data_bases import PlayerDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/get")
def get(
    request: Request,
    discord_id: Optional[str] = Query(None),
    steam_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    results = []

    if discord_id:
        data = PlayerDB.get_pdata_discord(discord_id)
        if data:
            results.append(data)

    elif steam_id:
        data = PlayerDB.get_pdata_steam(steam_id)
        if data:
            results.append(data)

    elif name:
        results.extend(PlayerDB.get_pdata_name(name))

    else:
        results = PlayerDB.get_pdata_all()

    return [
        {
            "id": u_id,
            "discord_id": pdata.discord_id,
            "steam_id": pdata.steam_id,
            "payments_uuid": pdata.payments_uuid,
        }
        for u_id, pdata in results
    ]
