from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt

from data_control import Config

# === настройки ===
CLIENT_ID = "1370825296839839795"
CLIENT_SECRET = Config.discord_app()
REDIRECT_URI = "https://spf-base.ru/api_v2/oauth2/discord/callback"
JWT_SECRET = Config.jwt_key()
DISCORD_API = "https://discord.com/api"


router = APIRouter()


def create_jwt(data: dict) -> str:
    data = data.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode(data, JWT_SECRET, algorithm="HS256")


def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

    except JWTError:
        return None


@router.get("/me")
def me(request: Request):
    token = request.cookies.get("session")
    if not token:
        return JSONResponse({"authenticated": False})

    data = decode_jwt(token)
    if not data:
        return JSONResponse({"authenticated": False})

    return {"authenticated": True, "user": data}


@router.get("/discord/login")
def login():
    query = urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify",
        }
    )
    return RedirectResponse(f"{DISCORD_API}/oauth2/authorize?{query}")


@router.get("/discord/callback")
def callback(code: str | None = None):
    if not code:
        raise HTTPException(400, "Missing code")

    token_resp = requests.post(
        f"{DISCORD_API}/oauth2/token",
        data={
            "client_id": CLIENT_ID,
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
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if me_resp.status_code != 200:
        raise HTTPException(400, "Failed to fetch user profile")

    me = me_resp.json()

    jwt_token = create_jwt({"discord_id": me["id"], "username": me["username"]})
    resp = RedirectResponse("/")
    resp.set_cookie("session", jwt_token, httponly=True, secure=False)
    return resp
