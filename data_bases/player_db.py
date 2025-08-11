import json
from dataclasses import asdict, dataclass, field, fields
from enum import Enum

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


@dataclass
class PlayerData:
    discord_name: str | None = None
    discord_avatar: str | None = None

    payments_uuid: list[str] = field(default_factory=list)

    blacklist: dict[str, bool] = field(
        default_factory=lambda: {
            "admin": False,
            "lore": False,
        }
    )

    note: list[NoteData] = field(default_factory=list)

    mb_limit: float = 0
    mb_taken: float = 0
    initialized: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "PlayerData":
        valid_keys = {f.name for f in fields(cls)}
        clean = {k: v for k, v in raw.items() if k in valid_keys}

        if "note" in clean and isinstance(clean["note"], list):
            clean["note"] = [
                NoteData.from_dict(n) if isinstance(n, dict) else n
                for n in clean["note"]
            ]

        clean.setdefault("initialized", False)
        clean.setdefault("mb_limit", 0.0)
        clean.setdefault("mb_taken", 0.0)

        return cls(**clean)


class PlayerDB(BaseDB):
    _db_name = "player"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()
        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS player_unit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT,
                    steam_id TEXT,
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
        with cls._connect() as con:
            cur = con.execute(
                "INSERT INTO player_unit (discord_id, steam_id, data) VALUES (?, ?, ?)",
                (discord_id, steam_id, blob),
            )
            con.commit()
            return cur.lastrowid

    @classmethod
    def update_player(
        cls,
        u_id: int,
        discord_id: str | None,
        steam_id: str | None,
        data: PlayerData,
    ) -> None:
        blob = json.dumps(asdict(data))
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
    def add_payment(cls, u_id: int, payment_uuid: str) -> None:
        entry = cls.get_pdata_id(u_id)
        if not entry:
            raise ValueError("Player not found")

        u_id, _, _, data = entry
        if payment_uuid not in data.payments_uuid:
            data.payments_uuid.append(payment_uuid)
            cls._update_data(u_id, data)

    @classmethod
    def remove_payment(cls, u_id: int, payment_uuid: str) -> None:
        entry = cls.get_pdata_id(u_id)
        if not entry:
            raise ValueError("Player not found")

        u_id, _, _, data = entry
        if payment_uuid in data.payments_uuid:
            data.payments_uuid.remove(payment_uuid)
            cls._update_data(u_id, data)

    @classmethod
    def _update_data(cls, u_id: int, data: PlayerData) -> None:
        blob = json.dumps(asdict(data))
        with cls._connect() as con:
            con.execute("UPDATE player_unit SET data = ? WHERE id = ?", (blob, u_id))
            con.commit()
