import json
import sqlite3
import urllib.request
from pathlib import Path

# from data_control import Config


class GameDBProcessor:
    DB_PATH = Path("data/game_server.db")
    JSON_PATH = Path("data/game_server.json")

    @classmethod
    def download_db(cls) -> None:
        urllib.request.urlretrieve(Config.game_server_ftp(), cls.DB_PATH)

    @classmethod
    def cleanup_db(cls) -> None:
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
    def drop_json(cls) -> Path:
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
    def delete_db(cls) -> None:
        if cls.DB_PATH.exists():
            cls.DB_PATH.unlink()


conn = sqlite3.connect(GameDBProcessor.DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT char_id, json
    FROM spf2_char_data
    WHERE key = 'inventory' AND json LIKE '%"currency_subsidies"%'
""")
rows = cursor.fetchall()
conn.close()

result = []

for char_id, json_str in rows:
    try:
        data = json.loads(json_str)
    except Exception:
        continue

    for item in data.get("items", []):
        if item.get("id") == "currency_subsidies":
            count = item.get("count", 0)
            try:
                count = int(count)
            except Exception:
                count = 0
            result.append((char_id, count))

result.sort(key=lambda x: x[1], reverse=True)

for char_id, count in result:
    print(char_id, count)
