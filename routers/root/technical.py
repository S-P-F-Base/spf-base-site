from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

router = APIRouter()
AUDIO_DIR = Path("data/audio")


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    content = """
User-agent: *
Disallow: /api/
Disallow: /api_v2/
Disallow: /profile/
"""
    return content.strip()


@router.get("/.well-known/discord", response_class=PlainTextResponse)
def well_known_discord():
    content = "dh=60795f3ac4184d38f6942a1963cb65ee9891885c"
    return content.strip()


@router.get("/data/audio/{file_name}")
def get_audio(file_name: str):
    if not file_name or file_name.strip() != file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    safe_path = Path(file_name)
    if safe_path.is_absolute() or any(part == ".." for part in safe_path.parts):
        raise HTTPException(status_code=400, detail="Invalid file path")

    file_path = AUDIO_DIR / safe_path

    try:
        file_path.resolve().relative_to(AUDIO_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    return FileResponse(file_path, media_type="audio/mpeg", filename=file_name)
