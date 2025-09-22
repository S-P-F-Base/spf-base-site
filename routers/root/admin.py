from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_control import PlayerSession
from templates import templates

router = APIRouter()


def access(request: Request):
    session = PlayerSession(request)
    pdata = session.get_player()

    if not pdata:
        return RedirectResponse("/api/discord/login", status_code=302)

    u_id, discord_id, steam_id, data = pdata
    if u_id != 1:  # bruh
        return RedirectResponse("/", status_code=302)

    return None


@router.get("/admin")
def admin_index(request: Request):
    tmp = access(request)
    if tmp is not None:
        return tmp

    return templates.TemplateResponse("admin/index.html", {"request": request})


@router.get("/admin/players")
def admin_players(request: Request):
    tmp = access(request)
    if tmp is not None:
        return tmp

    return templates.TemplateResponse("admin/players.html", {"request": request})
