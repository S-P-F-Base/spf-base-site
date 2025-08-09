from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


COLLECTION_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=3466203256"


def mods_redirect():
    return RedirectResponse(COLLECTION_URL, status_code=302)


for path in ("/server_mods", "/server_collection", "/workshop", "/addons"):
    router.add_api_route(path, mods_redirect, methods=["GET"])
