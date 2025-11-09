import asyncio
import json
from pathlib import Path
from typing import Literal

from requests import Session

from .config import Config


class ServerControl:
    _cache: dict[str, str | None] = {"text": None}

    _session = Session()

    status_ttl = 300

    base_url = "https://panel.ark-hoster.ru/servers/control/"
    status_url = "gsDataInfo/20011"
    stop_url = "action/20011/stop"
    start_url = "action/20011/start"

    cache_data = Path("data/server_status_cache.json")

    @classmethod
    def _load_cache(cls) -> None:
        if not cls.cache_data.exists():
            return

        try:
            with cls.cache_data.open("r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cache["text"] = data["text"]

        except Exception:
            pass

    @classmethod
    def _save_cache(cls) -> None:
        try:
            with cls.cache_data.open("w", encoding="utf-8") as f:
                json.dump({"text": cls._cache["text"]}, f)

        except Exception:
            pass

    @classmethod
    def setup(cls) -> None:
        cls._session.cookies.update(Config.hosting_cookies())
        cls._load_cache()

    @classmethod
    def get_status(cls) -> str | None:
        return cls._cache["text"]

    @classmethod
    def _get_status(cls) -> str | None:
        try:
            resp = cls._session.get(cls.base_url + cls.status_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        except Exception:
            return cls._cache["text"]

        status = str(data.get("server_status"))

        match status:
            case "1":
                text = "Выключен"

            case "2":
                text = "Включен"

            case _:
                text = "ХЗ"

        cls._cache["text"] = text
        cls._save_cache()
        return text

    @classmethod
    def perform_action(cls, action: Literal["start", "stop"]) -> None:
        try:
            url = cls.base_url + getattr(cls, f"{action}_url")
            resp = cls._session.get(url)
            resp.raise_for_status()

        except Exception as e:
            raise RuntimeError(f"Failed to {action} server: {e}")

        cls._get_status()

    @classmethod
    async def server_status_updater(cls):
        while True:
            try:
                cls._get_status()

            except Exception:
                pass

            await asyncio.sleep(15)
