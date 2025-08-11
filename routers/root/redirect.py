from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


COLLECTION_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=3466203256"
DISCORD_URL = "https://discord.gg/JEzsQrKzbY"


def mods_redirect():
    return RedirectResponse(COLLECTION_URL, status_code=302)


def discord_redirect():
    return RedirectResponse(DISCORD_URL, status_code=302)


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
