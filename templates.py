from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve()
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory="templates")


@templates.env.filter("ver")
def static_with_version(file: str) -> str:
    static_path = BASE_DIR / "static/css" / file
    if static_path.exists():
        v = int(static_path.stat().st_mtime)
        return f"/static/css/{file}?v={v}"
    return f"/static/css/{file}"
