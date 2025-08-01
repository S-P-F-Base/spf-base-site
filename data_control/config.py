import json
import os
from typing import Any, Literal

from dotenv import load_dotenv


class Config:
    _loaded = False

    _cache = {}

    @classmethod
    def load(cls):
        if cls._loaded:
            return

        load_dotenv()

        for key in [
            "YOOMONEY_ACCOUNT",
            "YOOMONEY_NOTIFICATION",
            "JWT_KEY",
            "TAX_AGENT",
            "TAX_AUTHORIZATION",
            "TAX_INN",
            "OVERHOSTING_COOKIES",
            "RESEND_API",
            "STEAM_API",
            "DISCORD_BOT",
            "DISCORD_APP",
        ]:
            cls._cache[key] = os.getenv(key, None)

        for key, val in cls._cache.items():
            if val is None:
                raise RuntimeError(f"{key} not set in environment")

        cls._loaded = True

    # region env
    @classmethod
    def _base_get_env(cls, key: str) -> Any:
        if not cls._loaded:
            cls.load()

        return cls._cache[key]

    @classmethod
    def yoomoney_client_id(cls) -> str:
        return cls._base_get_env("YOOMONEY_CLIENT_ID")

    @classmethod
    def yoomoney_client_secret(cls) -> str:
        return cls._base_get_env("YOOMONEY_CLIENT_SECRET")

    @classmethod
    def yoomoney_account(cls) -> str:
        return cls._base_get_env("YOOMONEY_ACCOUNT")

    @classmethod
    def yoomoney_notification(cls) -> str:
        return cls._base_get_env("YOOMONEY_NOTIFICATION")

    @classmethod
    def jwt_key(cls) -> str:
        return cls._base_get_env("JWT_KEY")

    @classmethod
    def tax_agent(cls) -> str:
        return cls._base_get_env("TAX_AGENT")

    @classmethod
    def tax_authorization(cls) -> str:
        return cls._base_get_env("TAX_AUTHORIZATION")

    @classmethod
    def tax_inn(cls) -> str:
        return cls._base_get_env("TAX_INN")

    @classmethod
    def overhosting_cookies(cls) -> dict:
        return json.loads(cls._base_get_env("OVERHOSTING_COOKIES"))

    @classmethod
    def resend_api(cls) -> str:
        return cls._base_get_env("RESEND_API")

    @classmethod
    def steam_api(cls) -> str:
        return cls._base_get_env("STEAM_API")

    @classmethod
    def discord_bot(cls) -> str:
        return cls._base_get_env("DISCORD_BOT")

    @classmethod
    def discord_app(cls) -> str:
        return cls._base_get_env("DISCORD_APP")

    # endregion

    # region commission
    @classmethod
    def user_pays_commission(cls) -> bool:
        return False

    @classmethod
    def get_commission_rates(cls, key: Literal["PC", "AC"]) -> float:
        commission_rates = {
            "PC": 0.01,  # Yoomoney
            "AC": 0.03,  # Банковская карта
        }.get(key, None)
        if commission_rates is None:
            raise ValueError(f"Unknown key for get_commission_rates {key}")

        return commission_rates

    # endregion

    # region proxy
    @classmethod
    def proxy(cls) -> dict:
        return {  # РКН привет
            "http": "socks5h://127.0.0.1:1080",
            "https": "socks5h://127.0.0.1:1080",
        }

    # endregion

    # region discord
    @classmethod
    def discord_guild_id(cls) -> str:
        return "1321306723423883284"

    @classmethod
    def discord_oauth2(cls) -> str:
        return "https://discord.com/oauth2/authorize?client_id=1370825296839839795&response_type=code&redirect_uri=https%3A%2F%2Fspf-base.ru%2Fapi%2Fdiscord%2Fredirect&scope=identify+guilds+guilds.join"

    # endregion
