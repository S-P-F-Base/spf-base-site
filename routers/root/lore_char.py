import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from templates import templates

router = APIRouter()

LORE_CHAR_DATA = Path("data/lore_char.json")


@router.get("/lore_char", response_class=HTMLResponse)
def lore_char(request: Request):
    lore_dict = {}
    if LORE_CHAR_DATA.exists():
        lore_dict = json.loads(LORE_CHAR_DATA.read_text())

    return templates.TemplateResponse(
        "lore_char.html", {"request": request, "lore_dict": lore_dict}
    )
