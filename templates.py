from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory="templates")


def static_with_version(file: str) -> str:
    static_path = STATIC_DIR / "css" / file
    if static_path.exists():
        v = int(static_path.stat().st_mtime)
        return f"/static/css/{file}?v={v}"
    
    return f"/static/css/{file}"


templates.env.filters["ver"] = static_with_version
