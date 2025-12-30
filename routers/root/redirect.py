from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from utils import Constant

router = APIRouter()


def mods_redirect():
    url = Constant.get("steam_url")
    if url is None:
        raise HTTPException(500, detail="steam_url not set")

    return RedirectResponse(url, status_code=302)


def discord_redirect():
    url = Constant.get("discord_url")
    if url is None:
        raise HTTPException(500, detail="discord_url not set")

    return RedirectResponse(url, status_code=302)


for path in (
    "/server_mods",
    "/server_collection",
    "/workshop",
    "/addons",
    "/mods",
):
    router.add_api_route(path, mods_redirect, methods=["GET"])

for path in (
    "/discord",
    "/ds",
):
    router.add_api_route(path, discord_redirect, methods=["GET"])
