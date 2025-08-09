from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from data_control import Config

router = APIRouter()


@router.get("/login")
def login():
    return RedirectResponse(Config.discord_oauth2(), status_code=302)
