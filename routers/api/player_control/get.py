from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder

from data_bases import PlayerDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/get")
def get(
    request: Request,
    discord_id: Optional[str] = Query(None),
    steam_id: Optional[str] = Query(None),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.READ_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    results = []

    if discord_id:
        result = PlayerDB.get_pdata_discord(discord_id)
        if result:
            results.append(result)

    elif steam_id:
        result = PlayerDB.get_pdata_steam(steam_id)
        if result:
            results.append(result)

    else:
        results = PlayerDB.get_pdata_all()

    return [
        {
            "id": u_id,
            "discord_id": discord_id,
            "steam_id": steam_id,
            "data": jsonable_encoder(pdata),
        }
        for u_id, discord_id, steam_id, pdata in results
    ]
