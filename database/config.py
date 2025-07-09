import os

from dotenv import load_dotenv


class Config:
    _loaded = False

    _cache = {}

    @classmethod
    def load(cls):
        if cls._loaded:
            return

        load_dotenv()

        cls._cache["YOOMONEY_ACCOUNT"] = os.getenv("YOOMONEY_ACCOUNT", None)
        cls._cache["YOOMONEY_NOTIFICATION"] = os.getenv("YOOMONEY_NOTIFICATION", None)
        cls._cache["BOT_TOKEN"] = os.getenv("BOT_TOKEN", None)
        cls._cache["JWT_KEY"] = os.getenv("JWT_KEY", None)

        for key, val in cls._cache.items():
            if val is None:
                raise RuntimeError(f"{key} not set in environment")

        cls._loaded = True

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
