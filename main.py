from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Config, LogDB, UserDB, YoomoneyDB
from routers.api.auth import api_auth_login, api_auth_refresh
from routers.api.yoomoney import (
    yoomoney_create_payment,
    yoomoney_create_payment_url,
    yoomoney_notification,
)
from routers.root import (
    root_discord,
    root_download,
    root_index,
    root_pay,
    root_robots,
    root_wiki,
)

ALLOWED_PATHS = {"/api/yoomoney/notification"}
REQUIRED_AGENT = "spf-agent-v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Config.load()
        LogDB.create_db_table()
        UserDB.create_db_table()
        YoomoneyDB.create_db_table()

        yield

    finally:
        pass


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

templates = Jinja2Templates(directory="templates")


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

    elif exc.status_code == 502:
        return templates.TemplateResponse(
            "error_code/502.html",
            {"request": request},
            status_code=502,
        )

    return HTMLResponse(content=exc.detail, status_code=exc.status_code)


# /
app.include_router(root_discord)
app.include_router(root_download)
app.include_router(root_index)
app.include_router(root_pay)
app.include_router(root_robots)
app.include_router(root_wiki)

# /api/auth
app.include_router(api_auth_login, prefix="/api/auth")
app.include_router(api_auth_refresh, prefix="/api/auth")


# /api/yoomoney
app.include_router(yoomoney_notification, prefix="/api/yoomoney")
app.include_router(yoomoney_create_payment, prefix="/api/yoomoney")
app.include_router(yoomoney_create_payment_url, prefix="/api/yoomoney")
