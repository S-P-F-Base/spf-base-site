from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()
HTML_DIR = Path("templates/game")


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
