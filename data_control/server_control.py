import asyncio
import json
from pathlib import Path
from typing import Literal

from requests import Session

from .config import Config


class ServerControl:
    _cache: dict[str, str | None] = {"text": None}
    _last_status: str | None = None

    _session = Session()

    status_ttl = 300
    base_url = "https://my.overhosting.ru/servers/control"
    status_url = base_url + "/ajaxaction/32620/get_server_status"
    action_url = base_url + "/action/32620/"

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
        cls._session.cookies.update(Config.overhosting_cookies())
        cls._load_cache()

    @classmethod
    def get_status(cls) -> str | None:
        return cls._cache["text"]

    @classmethod
    def _get_status(cls) -> str | None:
        if cls._last_status is not None and cls._last_status != "working":
            return cls._cache["text"]

        try:
            resp = cls._session.get(cls.status_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        except Exception:
            return cls._cache["text"]

        status = data.get("status")
        cls._last_status = status

        match status:
            case "success":
                cls.status_ttl = 300
                text = data.get("badge_text")

            case "working":
                cls.status_ttl = 5
                text = data.get("description")

            case _:
                cls.status_ttl = 300
                text = data.get("description", cls._cache["text"])

        cls._cache["text"] = text
        cls._save_cache()
        return text

    @classmethod
    def perform_action(cls, action: Literal["start", "stop"]) -> None:
        try:
            resp = cls._session.get(f"{cls.action_url}/{action}")
            resp.raise_for_status()

        except Exception as e:
            raise RuntimeError(f"Failed to {action} server: {e}")

        cls._last_status = None
        cls._get_status()

    @classmethod
    async def server_status_updater(cls):
        while True:
            try:
                cls._get_status()

            except Exception:
                pass

            await asyncio.sleep(15)
