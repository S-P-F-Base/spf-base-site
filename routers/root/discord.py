from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/discord")
def discord():
    return RedirectResponse("https://discord.gg/JEzsQrKzbY", status_code=302)
