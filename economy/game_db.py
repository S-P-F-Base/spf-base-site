import asyncio
import json
import sqlite3
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from data_control import Config, ServerControl


class GameDBProcessor:
    DB_PATH = Path("data/game_server.db")
    JSON_PATH = Path("data/game_server.json")

    @classmethod
    def _download_db(cls) -> None:
        urllib.request.urlretrieve(Config.game_server_ftp(), cls.DB_PATH)

    @classmethod
    def _cleanup_db(cls) -> None:
        if not cls.DB_PATH.exists():
            raise FileNotFoundError("Database file not found. Download it first.")

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        protected = {"spf2_char_data", "sqlite_sequence"}

        for table in tables:
            if table not in protected:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

        cursor.execute("DELETE FROM spf2_char_data WHERE key != 'inventory'")

        conn.commit()
        conn.close()

    @classmethod
    def _drop_json(cls) -> Path:
        if not cls.DB_PATH.exists():
            raise FileNotFoundError("Database file not found. Download it first.")

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT char_id, json FROM spf2_char_data WHERE key = 'inventory'"
        )
        rows = cursor.fetchall()
        conn.close()

        totals: dict[str, int] = {}

        for _, json_str in rows:
            try:
                payload = json.loads(json_str)

            except Exception:
                continue

            items = payload.get("items")
            if not isinstance(items, list):
                continue

            for it in items:
                if not isinstance(it, dict):
                    continue

                item_id = it.get("id")
                if not item_id:
                    continue

                cnt_raw = it.get("count", 1)
                try:
                    cnt = int(cnt_raw)

                except Exception:
                    cnt = 1

                totals[item_id] = totals.get(item_id, 0) + cnt

        merged_list = [
            {"id": iid, "count": cnt}
            for iid, cnt in sorted(totals.items(), key=lambda x: (-x[1], x[0]))
        ]

        cls.JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.JSON_PATH, "w", encoding="utf-8") as f:
            json.dump({"inventory": merged_list}, f, ensure_ascii=False, indent=4)

        return cls.JSON_PATH

    @classmethod
    def _delete_db(cls) -> None:
        if cls.DB_PATH.exists():
            cls.DB_PATH.unlink()

    @classmethod
    def create_json(cls) -> Path:
        cls._download_db()
        cls._cleanup_db()
        cls._drop_json()
        cls._delete_db()

        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        snap_path = cls.JSON_PATH.parent / "snapshots" / f"inv_{ts}.json"
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        cls.JSON_PATH.rename(snap_path)

        return snap_path

    @classmethod
    async def pull_db_data(cls):
        while True:
            try:
                if ServerControl.get_status() == "Включен":
                    cls.create_json()

            except Exception:
                pass

            await asyncio.sleep(60 * 15)
