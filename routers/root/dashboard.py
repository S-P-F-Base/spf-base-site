from dataclasses import asdict

import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_bases import PlayerDB
from data_control import Config, PlayerSession
from templates import templates

router = APIRouter()


ROLE_VIP = "1389261673726218260"


def discord_member_has_role(discord_user_id: str, role_id: str) -> bool:
    url = f"https://discord.com/api/v10/guilds/{Config.discord_guild_id()}/members/{discord_user_id}"
    headers = {"Authorization": f"Bot {Config.discord_bot()}"}

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=5,
            proxies=Config.proxy(),
        )

        if r.status_code != 200:
            return False

        data = r.json()
        roles = data.get("roles", [])
        return role_id in roles

    except Exception:
        return False


@router.get("/dashboard")
def dashboard(request: Request):
    session = PlayerSession(request)
    pdata = session.get_player()

    if not pdata:
        return RedirectResponse("/api/discord/login", status_code=302)

    u_id, discord_id, steam_id, data = pdata

    if discord_id and not data.initialized:
        has_vip = discord_member_has_role(discord_id, ROLE_VIP)
        data.mb_limit = 75 if has_vip else 50
        data.initialized = True
        PlayerDB.update_player(u_id, discord_id, steam_id, data)

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "discord_id": discord_id,
            "steam_id": steam_id,
            "player_id": u_id,
            "data": asdict(data),
        },
    )
