import re

import requests
from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import LogDB, LogType, PlayerData, PlayerDB, UserAccess, UserDB
from data_control import Config, req_authorization

router = APIRouter()


# region discord
def get_discord_id_by_name(username: str) -> tuple[str, str, str]:
    response = requests.get(
        f"https://discord.com/api/v10/guilds/{Config.discord_guild_id()}/members/search",
        headers={"Authorization": f"Bot {Config.discord_bot()}"},
        params={"query": username},
        proxies=Config.proxy(),
    )
    response.raise_for_status()
    members = response.json()

    if not members:
        raise ValueError("Unable to get discord user information")

    return (
        members[0]["user"]["id"],
        members[0]["user"]["global_name"],
        members[0]["user"]["avatar"],
    )


# endregion


# region steam
STEAMID64_BASE = 76561197960265728


def resolve_vanity_url(vanity: str) -> str:
    resp = requests.get(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
        params={"key": Config.steam_api(), "vanityurl": vanity},
        proxies=Config.proxy(),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("response", {}).get("success") != 1:
        raise ValueError("Vanity URL not found or API error")

    return data["response"]["steamid"]


def steam2_to_64(steam2: str) -> str:
    m = re.fullmatch(r"STEAM_(\d+):([01]):(\d+)", steam2, flags=re.IGNORECASE)
    if not m:
        raise ValueError("Invalid Steam2 ID format")

    y = int(m.group(2))
    z = int(m.group(3))
    account_id = z * 2 + y

    return str(STEAMID64_BASE + account_id)


def steam3_to_64(steam3: str) -> str:
    m = re.fullmatch(r"\[([A-Za-z]):(\d+):(\d+)\]", steam3)
    if not m:
        raise ValueError("Invalid Steam3 ID format")

    account_id = int(m.group(3))

    return str(STEAMID64_BASE + account_id)


def get_steamid64(steam_input: str) -> str:
    s = steam_input.strip()

    if re.fullmatch(r"\d{17}", s):
        return s

    if s.upper().startswith("STEAM_"):
        return steam2_to_64(s)

    if s.startswith("[") and s.endswith("]"):
        return steam3_to_64(s)

    if "steamcommunity.com" in s:
        m = re.search(r"/profiles/(\d{17})", s)
        if m:
            return m.group(1)

        m = re.search(r"/id/([\w\d_-]+)", s)
        if m:
            vanity = m.group(1)
            return resolve_vanity_url(vanity)

        raise ValueError("Unsupported Steam URL format")

    if re.fullmatch(r"[\w\d_-]{2,32}", s):
        return resolve_vanity_url(s)

    raise ValueError("Unsupported Steam identifier")


# endregion


@router.post("/create")
def create(
    request: Request,
    discord_name: str = Body(...),
    steam_url: str = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    # region resolve steam_id
    try:
        steamid64 = get_steamid64(steam_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Error contacting Steam API")
    # endregion

    # region resolve discord_id
    try:
        discord_id, discord_name, discord_avatar = get_discord_id_by_name(discord_name)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Error contacting Discord API")
    # endregion

    player = PlayerData(discord_name=discord_name, discord_avatar=discord_avatar)

    try:
        PlayerDB.add_player(discord_id=discord_id, steam_id=steamid64, data=player)

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    LogDB.add_log(
        LogType.PLAYER_CREATED,
        f"Player {discord_id=}, {steamid64=} created",
        username,
    )

    return 200
