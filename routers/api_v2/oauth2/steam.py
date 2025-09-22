from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .utils import create_jwt, merge_with_old

REDIRECT_URI = "https://spf-base.ru/api_v2/oauth2/steam/callback"
STEAM_OPENID = "https://steamcommunity.com/openid/login"

router = APIRouter()


@router.get("/steam/login")
def steam_login():
    query = urlencode(
        {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": REDIRECT_URI,
            "openid.realm": "https://spf-base.ru",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
    )
    return RedirectResponse(f"{STEAM_OPENID}?{query}")


@router.get("/steam/callback")
def steam_callback(request: Request):
    params = dict(request.query_params)
    verify = params.copy()
    verify["openid.mode"] = "check_authentication"

    resp = requests.post(STEAM_OPENID, data=verify, timeout=10)
    if resp.status_code != 200 or "is_valid:true" not in resp.text:
        raise HTTPException(400, "Failed to verify OpenID response")

    claimed_id = params.get("openid.claimed_id")
    if not claimed_id:
        raise HTTPException(400, "Missing claimed_id")

    steam_id = claimed_id.rsplit("/", 1)[-1]

    merged = merge_with_old(request, {"steam_id": steam_id})
    jwt_token = create_jwt(merged)

    resp = RedirectResponse("/")
    resp.set_cookie("session", jwt_token, httponly=True, secure=True)
    return resp
