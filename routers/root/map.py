import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

router = APIRouter()

TEMPLATES = Path("templates")
STATIC_DIR = Path("static")
MAP_JSON = STATIC_DIR / "map" / "world.json"


@router.get("/map_edit")
def map_page():
    return HTMLResponse((TEMPLATES / "map.html").read_text(encoding="utf-8"))


@router.get("/map-data")
def map_data():
    if not MAP_JSON.exists():
        MAP_JSON.parent.mkdir(parents=True, exist_ok=True)
        MAP_JSON.write_text("{}", encoding="utf-8")

    return JSONResponse(json.loads(MAP_JSON.read_text(encoding="utf-8")))


@router.get("/map-download-default")
def map_download_default():
    return FileResponse(
        MAP_JSON,
        media_type="application/json",
        filename="world.default.json",
    )
