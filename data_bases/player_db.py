import json
from dataclasses import MISSING, asdict, dataclass, field, fields
from enum import Enum
from sqlite3 import IntegrityError
from typing import Any

from .base_db import BaseDB


class NoteStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


@dataclass
class NoteData:
    author: str
    value: str

    status: NoteStatus
    last_status_envoke_author: str

    @classmethod
    def from_dict(cls, raw: dict) -> "NoteData":
        valid_keys = {f.name for f in fields(cls)}
        clean = {k: v for k, v in raw.items() if k in valid_keys}

        if isinstance(clean.get("status"), str):
            try:
                clean["status"] = NoteStatus(clean["status"])

            except ValueError:
                clean["status"] = NoteStatus.ACTIVE

        return cls(**clean)


def _default_admin_access() -> dict[str, bool]:
    return {
        "admin": False,
        # player control
        "player_read": False,
        "player_create": False,
        "player_edit": False,
        "player_delete": False,
    }


def _default_blacklist() -> dict[str, bool]:
    return {"admin": False, "char": False, "lore": False}


@dataclass
class PlayerData:
    discord_name: str | None = None
    discord_avatar: str | None = None

    admin_access: dict[str, bool] = field(default_factory=_default_admin_access)

    blacklist: dict[str, bool] = field(default_factory=_default_blacklist)
    note: list[NoteData] = field(default_factory=list)

    mb_base_limit: float = 0
    mb_limit: float = 0
    mb_taken: float = 0

    initialized: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PlayerData":
        init_data: dict[str, Any] = {}

        for f in fields(cls):
            key = f.name
            val = raw.get(key, MISSING)

            if val is MISSING:
                if f.default is not MISSING:
                    init_data[key] = f.default

                elif f.default_factory is not MISSING:
                    init_data[key] = f.default_factory()

                else:
                    init_data[key] = None

                continue

            if key == "note":
                if isinstance(val, list):
                    init_data[key] = [
                        NoteData.from_dict(n) if isinstance(n, dict) else n for n in val
                    ]

                else:
                    init_data[key] = []

                continue

            if key == "blacklist":
                base = _default_blacklist()
                if isinstance(val, dict):
                    init_data[key] = {k: bool(val.get(k, base[k])) for k in base}

                else:
                    init_data[key] = base

                continue

            if key == "admin_access":
                base = _default_admin_access()
                if isinstance(val, dict):
                    init_data[key] = {k: bool(val.get(k, base[k])) for k in base}

                else:
                    init_data[key] = base

                continue

            init_data[key] = val

        return cls(**init_data)


class PlayerDB(BaseDB):
    _db_name = "player"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()
        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS player_unit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT UNIQUE,
                    steam_id TEXT UNIQUE,
                    data TEXT
                )
            """)
            con.commit()

    @classmethod
    def add_player(
        cls,
        discord_id: str | None,
        steam_id: str | None,
        data: PlayerData,
    ) -> int | None:
        blob = json.dumps(asdict(data))
        try:
            with cls._connect() as con:
                cur = con.execute(
                    "INSERT INTO player_unit (discord_id, steam_id, data) VALUES (?, ?, ?)",
                    (discord_id, steam_id, blob),
                )
                con.commit()
                return cur.lastrowid

        except IntegrityError as e:
            msg = str(e)
            if "player_unit.discord_id" in msg:
                raise ValueError("Duplicate discord_id") from e

            if "player_unit.steam_id" in msg:
                raise ValueError("Duplicate steam_id") from e

            raise

    @classmethod
    def update_player(
        cls,
        u_id: int,
        discord_id: str | None,
        steam_id: str | None,
        data: PlayerData,
    ) -> None:
        blob = json.dumps(asdict(data))
        try:
            with cls._connect() as con:
                con.execute(
                    """
                    UPDATE player_unit 
                    SET discord_id = ?, steam_id = ?, data = ?
                    WHERE id = ?
                    """,
                    (discord_id, steam_id, blob, u_id),
                )
                con.commit()

        except IntegrityError as e:
            msg = str(e)
            if "player_unit.discord_id" in msg:
                raise ValueError("Duplicate discord_id") from e

            if "player_unit.steam_id" in msg:
                raise ValueError("Duplicate steam_id") from e

            raise

    @classmethod
    def remove_player(cls, u_id: int) -> None:
        with cls._connect() as con:
            con.execute("DELETE FROM player_unit WHERE id = ?", (u_id,))
            con.commit()

    @classmethod
    def _row_to_data(cls, row: tuple) -> tuple[int, str | None, str | None, PlayerData]:
        u_id, discord_id, steam_id, data_blob = row
        try:
            raw = json.loads(data_blob) if data_blob else {}
        except json.JSONDecodeError:
            raw = {}

        data = PlayerData.from_dict(raw)
        return u_id, discord_id, steam_id, data

    @classmethod
    def get_pdata_id(
        cls, u_id: int
    ) -> tuple[int, str | None, str | None, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, steam_id, data FROM player_unit WHERE id = ?",
                (u_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_discord(
        cls, discord_id: str
    ) -> tuple[int, str | None, str | None, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, steam_id, data FROM player_unit WHERE discord_id = ?",
                (discord_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_steam(
        cls, steam_id: str
    ) -> tuple[int, str | None, str | None, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, steam_id, data FROM player_unit WHERE steam_id = ?",
                (steam_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_all(cls) -> list[tuple[int, str | None, str | None, PlayerData]]:
        with cls._connect() as con:
            rows = con.execute(
                "SELECT id, discord_id, steam_id, data FROM player_unit"
            ).fetchall()
            return [cls._row_to_data(row) for row in rows]

    @classmethod
    def _update_data(cls, u_id: int, data: PlayerData) -> None:
        blob = json.dumps(asdict(data))
        with cls._connect() as con:
            con.execute("UPDATE player_unit SET data = ? WHERE id = ?", (blob, u_id))
            con.commit()
