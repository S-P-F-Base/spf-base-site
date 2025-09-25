import json
from typing import Any
from uuid import uuid4

from .base_db import BaseDB


class ProfileData:
    def __init__(self) -> None:
        self.is_admin: bool = False
        self.blacklist: dict[str, bool] = self.default_blacklist()
        self.chars: list[dict[str, Any]] = []
        self.limits: dict[str, Any] = self.default_limits()
        self.notes: list[dict[str, Any]] = []

    @property
    def has_blacklist(self) -> bool:
        return any(self.blacklist.values())

    @staticmethod
    def default_blacklist() -> dict[str, bool]:
        return {
            "chars": False,
            "lore_chars": False,
            "admin": False,
        }

    @staticmethod
    def default_limits() -> dict[str, Any]:
        return {
            "base_limit": 50,
            "donate_limit": 0,
            "base_char": 2,
            "donate_char": 0,
            "used": 0,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_admin": self.is_admin,
            "blacklist": self.blacklist,
            "chars": self.chars,
            "limits": self.limits,
            "notes": self.notes,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict())

    @classmethod
    def from_json(cls, value: str) -> "ProfileData":
        new_obj = cls()
        try:
            data = json.loads(value)
            if data is None or not isinstance(data, dict):
                return new_obj

        except Exception:
            return new_obj

        new_obj.is_admin = data.get("is_admin", False)
        new_obj.blacklist = data.get("blacklist", cls.default_blacklist())
        new_obj.chars = data.get("chars", [])
        new_obj.limits = data.get("limits", cls.default_limits())
        new_obj.notes = data.get("notes", [])

        return new_obj


class ProfileDataBase(BaseDB):
    _db_name = "profiles"

    @classmethod
    def setup_db(cls) -> None:
        cls.create_db_dir()

        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    uuid TEXT PRIMARY KEY,
                    discord_id TEXT UNIQUE,
                    steam_id TEXT UNIQUE,
                    data TEXT
                )
            """)
            con.commit()

    @classmethod
    def create_profile(
        cls,
        discord_id: str | None = None,
        steam_id: str | None = None,
    ) -> str:
        p_uuid = str(uuid4().hex).upper()
        p_data = ProfileData()

        with cls._connect() as con:
            con.execute(
                """
                INSERT INTO profile (uuid, discord_id, steam_id, data)
                VALUES (?, ?, ?, ?)
                """,
                (p_uuid, discord_id, steam_id, p_data.to_json()),
            )
            con.commit()

        return p_uuid

    @classmethod
    def update_profile(
        cls,
        uuid: str,
        discord_id: str | None = None,
        steam_id: str | None = None,
        data: ProfileData | None = None,
    ) -> bool:
        fields, values = [], []
        if discord_id is not None:
            fields.append("discord_id = ?")
            values.append(discord_id)

        if steam_id is not None:
            fields.append("steam_id = ?")
            values.append(steam_id)

        if data is not None:
            fields.append("data = ?")
            values.append(data.to_json())

        if not fields:
            return False

        values.append(uuid)
        sql = f"UPDATE profile SET {', '.join(fields)} WHERE uuid = ?"

        with cls._connect() as con:
            cur = con.execute(sql, values)
            con.commit()
            return cur.rowcount > 0

    @classmethod
    def delete_profile(cls, uuid: str) -> bool:
        with cls._connect() as con:
            cur = con.execute("DELETE FROM profile WHERE uuid = ?", (uuid,))
            con.commit()

            return cur.rowcount > 0

    # region geters
    @classmethod
    def _fetch_one(cls, field: str, value: str) -> dict | None:
        with cls._connect() as con:
            cur = con.execute(f"SELECT * FROM profile WHERE {field} = ?", (value,))
            row = cur.fetchone()

        if not row:
            return None

        columns = [col[0] for col in cur.description]
        record = dict(zip(columns, row))

        data_raw = record.get("data")
        if isinstance(data_raw, str) and data_raw:
            try:
                record["data"] = ProfileData.from_json(data_raw)

            except json.JSONDecodeError:
                record["data"] = ProfileData()

        else:
            record["data"] = ProfileData()

        return record

    @classmethod
    def get_profile_by_uuid(cls, value: str) -> dict | None:
        return cls._fetch_one("uuid", value)

    @classmethod
    def get_profile_by_discord(cls, value: str) -> dict | None:
        return cls._fetch_one("discord_id", value)

    @classmethod
    def get_profile_by_steam(cls, value: str) -> dict | None:
        return cls._fetch_one("steam_id", value)

    @classmethod
    def get_all_profiles(cls) -> list[dict]:
        with cls._connect() as con:
            cur = con.execute("SELECT uuid, discord_id, steam_id, data FROM profile")
            rows = cur.fetchall()

        out = []

        for uuid, discord_id, steam_id, data_json in rows:
            rec = {"uuid": uuid, "discord_id": discord_id, "steam_id": steam_id}
            try:
                rec["data"] = ProfileData.from_json(data_json)

            except Exception:
                rec["data"] = ProfileData()

            out.append(rec)

        return out

    # endregion
