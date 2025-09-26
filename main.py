import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import discord_bot
from data_bases import PaymentServiceDB
from data_class import ProfileDataBase
from data_control import AutoTax, Config, ServerControl
from routers.api.payment_control import router as api_payment_control
from routers.api.service_control import router as api_service_control
from routers.api.yoomoney import router as api_yoomoney
from routers.api_v2.oauth2 import router as api_v2_oauth2
from routers.root import router as root
from templates import templates

ALLOWED_PATHS = {
    "/api/yoomoney/notification",
    "/api/discord/login",
    "/api/discord/redirect",
    "/api/steam/login",
    "/api/steam/redirect",
}
REQUIRED_AGENT = "spf-agent-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Config.load()
        PaymentServiceDB.create_db_table()
        ProfileDataBase.setup_db()

        try:
            AutoTax.setup()

        except Exception as err:
            logging.error(f"AutoTax setup fail: {err}")

        ServerControl.setup()

        asyncio.create_task(AutoTax.run_queue_worker(interval_sec=60))
        asyncio.create_task(discord_bot.start())

        yield

        await discord_bot.stop()

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
    if (
        path.startswith("/api")
        and not path.startswith("/api_v2")
        and path not in ALLOWED_PATHS
    ):
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


app.include_router(api_payment_control, prefix="/api/payment_control")
app.include_router(api_service_control, prefix="/api/service_control")
app.include_router(api_yoomoney, prefix="/api/yoomoney")

app.include_router(api_v2_oauth2, prefix="/api_v2/oauth2")

app.include_router(root)
