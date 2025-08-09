from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_control import PlayerSession
from templates import templates

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request):
    session = PlayerSession(request)
    pdata = session.get_player()

    if not pdata:
        return RedirectResponse("/api/discord/login", status_code=302)

    u_id, discord_id, steam_id, data = pdata

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "discord_id": discord_id,
            "steam_id": steam_id,
            "player_id": u_id,
            "data": asdict(data),
        },
    )
