from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from data_control import Config

from .utils import create_jwt, merge_with_old

CLIENT_SECRET = Config.discord_app()
REDIRECT_URI = "https://spf-base.ru/api_v2/oauth2/discord/callback"

router = APIRouter()


@router.get("/discord/login")
def discord_login():
    query = urlencode(
        {
            "client_id": "1370825296839839795",
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify",
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

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
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

    merged = merge_with_old(
        request,
        {"discord_id": me["id"], "username": me["username"]},
    )
    jwt_token = create_jwt(merged)

    resp = RedirectResponse("/")
    resp.set_cookie("session", jwt_token, httponly=True, secure=True)
    return resp
