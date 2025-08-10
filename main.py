import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from data_bases import LogDB, PaymentServiceDB, PlayerDB, UserDB
from data_control import AutoTax, Config, MailControl, ServerControl
from routers.api.auth import router as api_auth
from routers.api.discord import router as api_discord
from routers.api.logs import router as api_logs
from routers.api.lore_char_control import router as api_lore_char_control
from routers.api.player_control import router as api_player_control
from routers.api.server_control import router as api_server_control
from routers.api.site_control import router as api_site_control
from routers.api.steam import router as api_steam
from routers.api.user_control import router as api_user_control
from routers.api.websocket import router as api_websocket
from routers.api.yoomoney import router as api_yoomoney
from routers.root import router as root
from templates import templates

ALLOWED_PATHS = {
    "/api/yoomoney/notification",
    "/api/discord/login",
    "/api/discord/redirect",
    "/api/steam/login",
    "/api/steam/redirect",
}
REQUIRED_AGENT = "spf-agent-v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Config.load()
        LogDB.create_db_table()
        UserDB.create_db_table()
        PlayerDB.create_db_table()
        PaymentServiceDB.create_db_table()

        try:
            AutoTax.setup()

        except Exception as err:
            logging.error(f"AutoTax setup fail: {err}")

        ServerControl.setup()
        MailControl.setup()

        asyncio.create_task(ServerControl.server_status_updater())

        yield

    finally:
        pass


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


if os.getenv("FASTAPISTATIC") == "1":
    app.mount("/static", StaticFiles(directory="static"), name="static")


# Validate user-agent for api
@app.middleware("http")
async def user_agent_blocker(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api") and path not in ALLOWED_PATHS:
        user_agent = request.headers.get("user-agent", "")
        if user_agent != REQUIRED_AGENT:
            return JSONResponse(status_code=403, content={"detail": "Invalid agent"})

    return await call_next(request)


# Error Code
@app.exception_handler(StarletteHTTPException)
def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    if exc.status_code == 403:
        return templates.TemplateResponse(
            "error_code/403.html",
            {"request": request},
            status_code=403,
        )

    elif exc.status_code == 404:
        return templates.TemplateResponse(
            "error_code/404.html",
            {"request": request},
            status_code=404,
        )

    elif exc.status_code == 418:
        return templates.TemplateResponse(
            "error_code/418.html",
            {"request": request},
            status_code=418,
        )

    elif exc.status_code == 500:
        return templates.TemplateResponse(
            "error_code/500.html",
            {"request": request},
            status_code=500,
        )

    elif exc.status_code == 502:
        return templates.TemplateResponse(
            "error_code/502.html",
            {"request": request},
            status_code=502,
        )

    return HTMLResponse(content=exc.detail, status_code=exc.status_code)


app.include_router(api_auth, prefix="/api/auth")
app.include_router(api_discord, prefix="/api/discord")
app.include_router(api_logs, prefix="/api/logs")
app.include_router(api_lore_char_control, prefix="/api/lore_char_control")
app.include_router(api_player_control, prefix="/api/player_control")
app.include_router(api_server_control, prefix="/api/server_control")
app.include_router(api_site_control, prefix="/api/site_control")
app.include_router(api_steam, prefix="/api/steam")
app.include_router(api_user_control, prefix="/api/user_control")
app.include_router(api_websocket, prefix="/api/websocket")
app.include_router(api_yoomoney, prefix="/api/yoomoney")
app.include_router(root)

if os.getenv("DEBUG") == "1":
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ", ".join(route.methods)
            path = route.path
            print(f"{methods} -> {path}")
