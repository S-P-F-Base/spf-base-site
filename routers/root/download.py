from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from templates import templates

router = APIRouter()


_FILES_BUILDS = [
    "linux-64bit",
    "linux-32bit",
    "linux-arm64",
    "windows-64bit",
    "windows-32bit",
    "windows-arm64",
]


@router.get("/download")
def download(request: Request):
    return templates.TemplateResponse("download.html", {"request": request})


@router.get("/download/version")
def get_current_version():
    version_file = Path("data/builds/version")

    if version_file.exists():
        version = version_file.read_text(encoding="utf-8").strip()
        return {"version": version}

    return HTMLResponse("Version file not found", status_code=404)


@router.get("/download/{os_name}")
def download_by_os(os_name: str):
    file_path = None

    if os_name.lower() in _FILES_BUILDS:
        file_path = Path("data/builds") / f"{os_name.lower()}.zip"

    if file_path and file_path.exists():
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    return HTMLResponse("File not found", status_code=404)
