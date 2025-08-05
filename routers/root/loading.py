import random
from pathlib import Path

import requests
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from data_control import Config
from templates import templates

router = APIRouter()
loading_images_dir = Path("static/images/loading")


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


def get_weighted_bg_url() -> str:
    candidates = []

    for path in loading_images_dir.glob("*.png"):
        name = path.name

        try:
            weight_str = name.split("_", 1)[0]
            weight = int(weight_str)
        except (ValueError, IndexError):
            continue

        candidates.extend([path] * weight)

    chosen = random.choice(candidates)
    return f"/static/images/loading/{chosen.name}"


@router.get("/loading", response_class=HTMLResponse)
def loading(request: Request, steamid: str = "", mapname: str = ""):
    name = resolve_name_from_steam(steamid) if steamid else "гость"
    bg_url = get_weighted_bg_url()

    return templates.TemplateResponse(
        "loading.html",
        {
            "request": request,
            "mapname": mapname,
            "bg_url": bg_url,
            "name": name,
        },
    )
