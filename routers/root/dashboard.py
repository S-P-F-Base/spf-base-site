from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_control import PlayerSession
from templates import templates

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request):
    session = PlayerSession(request)
    player = session.get_player()

    if not player:
        return RedirectResponse("/api/discord/login", status_code=302)

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "player": player,
        },
    )
