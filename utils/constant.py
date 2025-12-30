import json
import logging
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONSTANTS_PATH = BASE_DIR / "static/constants.json"


class Constant:
    _data = {}

    @classmethod
    def load(cls) -> None:
        try:
            with open(CONSTANTS_PATH, "r", encoding="utf-8") as f:
                cls._data = json.load(f)

        except FileNotFoundError:
            logging.warning(f"Constants file not found: {CONSTANTS_PATH}")
            cls._data = {}

        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in constants file: {e}")
            cls._data = {}

    @classmethod
    def get_all_data(cls) -> dict[str, str]:
        return cls._data.copy()

    @classmethod
    def get(cls, value: str, default: Any = None) -> Any:
        return cls._data.get(value, default)
