from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

import utils.jwt
from data_class import ProfileDataBase

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

    token = request.cookies.get("session")
    old = utils.jwt.decode(token) if token else None

    if not old:
        p_uuid = ProfileDataBase.get_profile_by_steam(steam_id)
        if p_uuid is None:
            p_uuid = ProfileDataBase.create_profile(steam_id=steam_id)
        else:
            p_uuid = p_uuid.get("uuid")
    else:
        uuid = old.get("uuid")
        if not uuid:
            raise HTTPException(400, "Invalid session: missing uuid")

        profile = ProfileDataBase.get_profile_by_uuid(uuid)
        if not profile:
            raise HTTPException(400, "Profile not found")

        if profile.get("steam_id"):
            raise HTTPException(400, "Steam account already linked")

        ProfileDataBase.update_profile(uuid, steam_id=steam_id)
        p_uuid = uuid

    jwt_token = utils.jwt.create({"uuid": p_uuid})

    resp = RedirectResponse("/profile")
    resp.set_cookie("session", jwt_token, httponly=True, secure=True)
    return resp
