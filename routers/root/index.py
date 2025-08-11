from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from data_control import ServerControl
from templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    status = ServerControl.get_status()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "server_status": status},
    )
