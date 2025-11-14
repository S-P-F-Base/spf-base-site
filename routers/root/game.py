import random
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from data_control import Config
from templates import templates

router = APIRouter()
HTML_DIR = Path("templates/game")
LOADING_MEDIA_DIR = Path("static/loading_media")


@router.get("/game/{file_name}")
def get_page(file_name: str):
    if not file_name or file_name.strip() != file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    safe_path = Path(file_name)
    if safe_path.is_absolute() or any(part == ".." for part in safe_path.parts):
        raise HTTPException(status_code=400, detail="Invalid file path")

    file_path = HTML_DIR / safe_path

    try:
        file_path.resolve().relative_to(HTML_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return HTMLResponse(file_path.read_text(encoding="utf-8"))


def resolve_name_from_steam(steamid: str) -> str:
    try:
        response = requests.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": Config.steam_api(), "steamids": steamid},
            timeout=3.0,
        )
        response.raise_for_status()
        players = response.json().get("response", {}).get("players", [])
        if players:
            return players[0].get("personaname", "гость")

    except Exception:
        pass

    return "гость"


def pick_weighted_media():
    candidates: list[Path] = []

    for path in LOADING_MEDIA_DIR.iterdir():
        if not path.is_file():
            continue

        ext = path.suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".mp4", ".webm"}:
            continue

        try:
            weight_str = path.name.split("_", 1)[0]
            weight = int(weight_str)
        except (ValueError, IndexError):
            continue

        candidates.extend([path] * weight)

    if not candidates:
        return None, None

    chosen: Path = random.choice(candidates)
    url = f"/static/loading_media/{chosen.name}"

    media_type = "video" if chosen.suffix.lower() in {".mp4", ".webm"} else "image"
    return url, media_type


@router.get("/loading", response_class=HTMLResponse)
def loading(request: Request, steamid: str = "", mapname: str = ""):
    name = resolve_name_from_steam(steamid) if steamid else "гость"
    media_url, media_type = pick_weighted_media()

    return templates.TemplateResponse(
        "loading.html",
        {
            "request": request,
            "mapname": mapname,
            "name": name,
            "media_url": media_url,
            "media_type": media_type,
        },
    )
