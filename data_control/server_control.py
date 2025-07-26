import datetime
import json
from datetime import UTC
from pathlib import Path
from typing import Literal

from requests import Session

from .config import Config

CACHE_PATH = Path("data/server_status_cache.json")
SAFE_MIN_DATETIME = datetime.datetime(2000, 1, 1, tzinfo=UTC)


class ServerControl:
    _cache = {
        "last_checked": SAFE_MIN_DATETIME,
        "status": None,
        "text": None,
    }

    _session = Session()
    STATUS_TTL = 60
    BASE_URL_HOST = "https://my.overhosting.ru/servers/control"
    STATUS_URL = BASE_URL_HOST + "/ajaxaction/32620/get_server_status"
    BASE_URL = BASE_URL_HOST + "/action/32620/"

    @classmethod
    def _load_cache(cls) -> None:
        if not CACHE_PATH.exists():
            return
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cache["last_checked"] = datetime.datetime.fromisoformat(
                    data["last_checked"]
                ).astimezone(UTC)
                cls._cache["status"] = data["status"]
                cls._cache["text"] = data["text"]
        except Exception:
            pass

    @classmethod
    def _save_cache(cls) -> None:
        try:
            with CACHE_PATH.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "last_checked": cls._cache["last_checked"].isoformat(),
                        "status": cls._cache["status"],
                        "text": cls._cache["text"],
                    },
                    f,
                )
        except Exception:
            pass

    @classmethod
    def setup(cls) -> None:
        cls._session.cookies.update(Config.overhosting_cookies())
        cls._load_cache()

    @classmethod
    def get_status(cls) -> tuple[str | None, str | None]:
        now = datetime.datetime.now(datetime.UTC)
        if (now - cls._cache["last_checked"]).total_seconds() < cls.STATUS_TTL:
            return cls._cache["status"], cls._cache["text"]

        try:
            resp = cls._session.get(cls.STATUS_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        except Exception as e:
            return None, f"Error: {e}"

        status = data.get("status")
        text = (
            data.get("badge_text") if status == "success" else data.get("description")
        )

        cls._cache.update(
            {
                "last_checked": now,
                "status": status,
                "text": text,
            }
        )
        cls._save_cache()

        return status, text

    @classmethod
    def perform_action(cls, action: Literal["start", "stop"]) -> None:
        try:
            resp = cls._session.get(f"{cls.BASE_URL}/{action}")
            resp.raise_for_status()

        except Exception as e:
            raise RuntimeError(f"Failed to {action} server: {e}")

        cls._cache["last_checked"] = SAFE_MIN_DATETIME
        cls._save_cache()
