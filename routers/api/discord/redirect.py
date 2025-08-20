import requests
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from data_bases import PlayerDB
from data_control import Config, PlayerSession
from templates import templates

router = APIRouter()


def exchange_code(code: str):
    data = {
        "client_id": "1370825296839839795",
        "client_secret": Config.discord_app(),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://spf-base.ru/api/discord/redirect",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(
        "https://discord.com/api/oauth2/token",
        headers=headers,
        proxies=Config.proxy(),
        data=data,
    )
    return response.json()


def get_user_info(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        "https://discord.com/api/users/@me",
        headers=headers,
        proxies=Config.proxy(),
    )
    return response.json()


def get_user_guilds(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers=headers,
        proxies=Config.proxy(),
    )
    return response.json()


def add_user_to_guild(user_id: str, access_token: str):
    url = (
        f"https://discord.com/api/guilds/{Config.discord_guild_id()}/members/{user_id}"
    )
    headers = {
        "Authorization": f"Bot {Config.discord_bot()}",
        "Content-Type": "application/json",
    }
    json_data = {"access_token": access_token}

    response = requests.put(
        url,
        headers=headers,
        json=json_data,
        proxies=Config.proxy(),
    )

    if response.status_code == 403 and "ban" in response.text.lower():
        return "banned", response.json()

    if response.status_code in (201, 204):
        return "joined", {"success": True}

    return "error", response.json()


@router.get("/redirect")
def redirect(request: Request):
    code = request.query_params.get("code")
    if not code:
        return templates.TemplateResponse(
            "auth_error.html",
            {"request": request, "reason": "Discord не отправил код авторизации."},
        )

    token_data = exchange_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        return templates.TemplateResponse(
            "auth_error.html",
            {"request": request, "reason": "Не удалось получить доступ от Discord."},
        )

    user = get_user_info(access_token)
    user_id = user.get("id")
    if not user_id:
        return templates.TemplateResponse(
            "auth_error.html",
            {"request": request, "reason": "Discord не отдал ID пользователя."},
        )

    guilds = get_user_guilds(access_token)
    guild_id = Config.discord_guild_id()

    if not any(g["id"] == guild_id for g in guilds):
        status, response = add_user_to_guild(user_id, access_token)

        if status == "banned":
            return templates.TemplateResponse(
                "auth_error.html",
                {
                    "request": request,
                    "reason": "Вы были ранее забанены на нашем сервере Discord. Подключение невозможно.",
                },
            )

        if status == "error":
            return templates.TemplateResponse(
                "auth_error.html",
                {
                    "request": request,
                    "reason": "Не удалось добавить вас на сервер. Попробуйте позже.",
                },
            )

    session = PlayerSession(request)
    session.sync_with_discord(
        discord_id=user_id,
        discord_name=user.get("global_name", ""),
        discord_avatar=user.get("avatar", ""),
    )

    player_entry = PlayerDB.get_pdata_discord(user_id)
    steam_id = player_entry[2] if player_entry else None

    jwt_token = session.create_token(discord_id=user_id, steam_id=steam_id)

    response = RedirectResponse(url="/player", status_code=302)
    response.set_cookie(
        key="session",
        value=jwt_token,
        httponly=True,
        secure=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )

    return response
