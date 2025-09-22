from dataclasses import asdict

import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_bases import PlayerDB
from data_control import Config, PlayerSession
from templates import templates

router = APIRouter()

ROLE_VIP = "1389261673726218260"


def fetch_discord_user(discord_id: str) -> tuple[str | None, str | None]:
    url = f"https://discord.com/api/v10/users/{discord_id}"
    headers = {"Authorization": f"Bot {Config.discord_bot()}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return None, None

        data = r.json()
        return data.get("username"), data.get("avatar")

    except Exception:
        return None, None


def discord_member_has_role(discord_user_id: str, role_id: str) -> bool:
    url = f"https://discord.com/api/v10/guilds/{Config.discord_guild_id()}/members/{discord_user_id}"
    headers = {"Authorization": f"Bot {Config.discord_bot()}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return False

        return role_id in r.json().get("roles", [])

    except Exception:
        return False


@router.get("/player")
def player(request: Request):
    session = PlayerSession(request)
    pdata = session.get_player()
    if not pdata:
        return RedirectResponse("/api/discord/login", status_code=302)

    u_id, discord_id, steam_id, data = pdata

    need_update = False

    if discord_id:
        live_name, live_avatar = fetch_discord_user(discord_id)

        if live_name and live_name != data.discord_name:
            data.discord_name = live_name
            need_update = True

        if live_avatar and live_avatar != data.discord_avatar:
            data.discord_avatar = live_avatar
            need_update = True

        if not data.initialized:
            has_vip = discord_member_has_role(discord_id, ROLE_VIP)
            data.mb_limit = 75 if has_vip else 50
            data.initialized = True
            need_update = True

    if need_update:
        PlayerDB.update_player(u_id, discord_id, steam_id, data)

    return templates.TemplateResponse(
        "player/index.html",
        {
            "request": request,
            "discord_id": discord_id,
            "steam_id": steam_id,
            "player_id": u_id,
            "data": asdict(data),
            "is_admin": bool(data.admin_access.get("admin", False)),
        },
    )
