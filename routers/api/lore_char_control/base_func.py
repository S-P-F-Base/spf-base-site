import json
from pathlib import Path
from typing import Any

LORE_CHAR_DATA = Path("data/lore_char.json")


def load_data() -> dict[str, Any]:
    if not LORE_CHAR_DATA.exists():
        return {}
    return json.loads(LORE_CHAR_DATA.read_text(encoding="utf-8"))


def save_data(data: dict[str, Any]):
    LORE_CHAR_DATA.write_text(
        json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8"
    )
