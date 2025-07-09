from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter()


_FILE_MAP = {
    "windows": Path("data/windows.zip"),
    # "mac": Path("data/mac.zip"),
    "linux": Path("data/linux.zip"),
}


def detect_os(user_agent: str) -> str | None:
    ua = user_agent.lower()
    if "windows" in ua:
        return "windows"
    elif "macintosh" in ua or "mac os" in ua:
        return "mac"
    elif "linux" in ua:
        return "linux"
    return None


@router.get("/download")
def download(request: Request):
    user_agent = request.headers.get("user-agent", "")
    os_name = detect_os(user_agent)

    if os_name is None:
        html_content = """
        <html>
            <body>
                <h2>Select your OS to download:</h2>
                <button onclick="window.location.href='/download/windows'">Windows</button>
                <!--<button onclick="window.location.href='/download/mac'">Mac</button>-->
                <button onclick="window.location.href='/download/linux'">Linux</button>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    file_path = _FILE_MAP.get(os_name)
    if file_path and file_path.exists():
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )
    else:
        return HTMLResponse("File not found for your OS", status_code=404)


@router.get("/download/{os_name}")
def download_by_os(os_name: str):
    file_path = _FILE_MAP.get(os_name.lower())
    if file_path and file_path.exists():
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    return HTMLResponse("File not found", status_code=404)
