import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_control import PlayerSession
from templates import templates

router = APIRouter()

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"


def verify_steam_openid(query_params) -> str | None:
    params = dict(query_params)
    params["openid.mode"] = "check_authentication"

    response = requests.post(
        "https://steamcommunity.com/openid/login",
        data=params,
    )

    if "is_valid:true" in response.text:
        claimed_id = query_params.get("openid.claimed_id", "")
        if claimed_id.startswith("https://steamcommunity.com/openid/id/"):
            return claimed_id.split("/")[-1]

    return None


@router.get("/redirect")
def redirect(request: Request):
    steam_id = verify_steam_openid(request.query_params)
    if not steam_id:
        return templates.TemplateResponse(
            "auth_error.html",
            {
                "request": request,
                "reason": "Ошибка авторизации через Steam.",
            },
        )

    session = PlayerSession(request)
    player = session.sync_with_steam(steam_id)
    jwt_token = session.create_token(player)

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="session",
        value=jwt_token,
        httponly=True,
        secure=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )

    return response
