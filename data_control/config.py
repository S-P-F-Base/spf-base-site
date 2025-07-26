import json
import os
from typing import Literal

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
            "BOT_TOKEN",
            "JWT_KEY",
            "TAX_AGENT",
            "TAX_AUTHORIZATION",
            "TAX_INN",
            "OVERHOSTING_COOKIES",
            "RESEND_API",
        ]:
            cls._cache[key] = os.getenv(key, None)

        for key, val in cls._cache.items():
            if val is None:
                raise RuntimeError(f"{key} not set in environment")

        cls._loaded = True

    # region env
    @classmethod
    def yoomoney_client_id(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["YOOMONEY_CLIENT_ID"]

    @classmethod
    def yoomoney_client_secret(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["YOOMONEY_CLIENT_SECRET"]

    @classmethod
    def yoomoney_account(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["YOOMONEY_ACCOUNT"]

    @classmethod
    def yoomoney_notification(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["YOOMONEY_NOTIFICATION"]

    @classmethod
    def bot_token(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["BOT_TOKEN"]

    @classmethod
    def jwt_key(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["JWT_KEY"]

    @classmethod
    def tax_agent(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["TAX_AGENT"]

    @classmethod
    def tax_authorization(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["TAX_AUTHORIZATION"]

    @classmethod
    def tax_inn(cls) -> str:
        if not cls._loaded:
            cls.load()

        return cls._cache["TAX_INN"]

    @classmethod
    def overhosting_cookies(cls) -> dict:
        if not cls._loaded:
            cls.load()

        return json.loads(cls._cache["OVERHOSTING_COOKIES"])

    @classmethod
    def resend_api(cls) -> dict:
        if not cls._loaded:
            cls.load

        return cls._cache["RESEND_API"]

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
