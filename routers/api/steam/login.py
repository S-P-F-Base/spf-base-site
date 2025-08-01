import urllib.parse

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"


@router.get("/login")
def login():
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": "https://spf-base.ru/api/steam/redirect",
        "openid.realm": "https://spf-base.ru/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    url = f"{STEAM_OPENID_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)
