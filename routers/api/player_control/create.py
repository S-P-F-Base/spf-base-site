import re

import requests
from fastapi import APIRouter, HTTPException, Request

from data_bases import LogDB, LogType, PlayerData, PlayerDB, UserAccess, UserDB
from data_control import Config, PlayerAPIData, req_authorization

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
def get_steamid64_from_url(url: str) -> str:
    match = re.search(r"/profiles/(\d{17})", url)
    if match:
        steam_id = match.group(1)
        return steam_id

    match = re.search(r"/id/([\w\d_-]+)", url)
    if match:
        vanity = match.group(1)
        return resolve_vanity_url(vanity)

    raise ValueError("Unsupported Steam URL format")


def resolve_vanity_url(vanity: str) -> str:
    response = requests.get(
        f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={Config.steam_api()}&vanityurl={vanity}"
    )
    response.raise_for_status()
    data = response.json()

    if data.get("response", {}).get("success") != 1:
        raise ValueError("Vanity URL not found or API error")

    return data["response"]["steamid"]


# endregion


@router.post("/create")
def create(request: Request, data: PlayerAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PLAYER):
        raise HTTPException(status_code=403, detail="Insufficient access")

    # region resolve steam_id
    try:
        steamid64 = get_steamid64_from_url(data.steam_url)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Error contacting Steam API")
    # endregion

    # region resolve discord_id
    try:
        discord_id, discord_name, discord_avatar = get_discord_id_by_name(
            data.discord_name
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Error contacting Discord API")
    # endregion

    player = PlayerData(discord_name=discord_name, discord_avatar=discord_avatar)
    PlayerDB.add_player(discord_id=discord_id, steam_id=steamid64, data=player)
    LogDB.add_log(
        LogType.PLAYER_CREATED,
        f"Player {discord_id=}, {steamid64=} created",
        username,
    )

    return 200
