from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/discord")
def discord():
    raise HTTPException(status_code=403, detail="Dead")
    return RedirectResponse("https://discord.gg/JEzsQrKzbY", status_code=302)
