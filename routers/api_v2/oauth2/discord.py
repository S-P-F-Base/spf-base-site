from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

import utils.jwt
from data_class import ProfileDataBase
from data_control import Config

CLIENT_SECRET = Config.discord_app()
REDIRECT_URI = "https://spf-base.ru/api_v2/oauth2/discord/callback"

BOT_TOKEN = Config.discord_bot()
GUILD_ID = str(Config.discord_guild_id())

router = APIRouter()


def _join_guild(user_id: str, access_token: str) -> int:
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}"
    payload = {"access_token": access_token}

    r = requests.put(
        url,
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    return r.status_code


@router.get("/discord/login")
def discord_login():
    query = urlencode(
        {
            "client_id": "1370825296839839795",
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify guilds.join",
            "prompt": "none",
        }
    )

    return RedirectResponse(f"https://discord.com/api/oauth2/authorize?{query}")


@router.get("/discord/callback")
def discord_callback(request: Request, code: str | None = None):
    if not code:
        raise HTTPException(400, "Missing code")

    token_resp = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": "1370825296839839795",
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if token_resp.status_code != 200:
        raise HTTPException(400, "Failed to exchange code")

    access_token = token_resp.json().get("access_token")
    if not access_token:
        raise HTTPException(400, "No access token")

    me_resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if me_resp.status_code != 200:
        raise HTTPException(400, "Failed to fetch user profile")

    me = me_resp.json()

    join_status = _join_guild(me["id"], access_token)
    if join_status not in (201, 204):
        pass

    token = request.cookies.get("session")
    old = utils.jwt.decode(token) if token else None

    if not old:
        p_uuid = ProfileDataBase.get_profile_by_discord(me["id"])
        if p_uuid is None:
            p_uuid = ProfileDataBase.create_profile(discord_id=me["id"])
        else:
            p_uuid = p_uuid.get("uuid")
    else:
        uuid = old.get("uuid")
        if not uuid:
            raise HTTPException(400, "Invalid session: missing uuid")

        profile = ProfileDataBase.get_profile_by_uuid(uuid)
        if not profile:
            raise HTTPException(400, "Profile not found")

        if profile.get("discord_id"):
            raise HTTPException(400, "Discord account already linked")

        ProfileDataBase.update_profile(uuid, discord_id=me["id"])
        p_uuid = uuid

    jwt_token = utils.jwt.create({"uuid": p_uuid})

    resp = RedirectResponse("/profile")
    resp.set_cookie("session", jwt_token, httponly=True, secure=True)
    return resp
