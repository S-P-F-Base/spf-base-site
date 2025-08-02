import pickle
from dataclasses import dataclass, field

from .base_db import BaseDB


@dataclass
class PlayerData:
    discord_name: str | None = None
    discord_avatar: str | None = None
    payments_uuid: list[str] = field(default_factory=list)


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
                    data BLOB
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
        blob = pickle.dumps(data)
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
        blob = pickle.dumps(data)
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
        data = pickle.loads(data_blob) if data_blob else PlayerData()
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
            cls._update_blob(u_id, data)

    @classmethod
    def remove_payment(cls, u_id: int, payment_uuid: str) -> None:
        entry = cls.get_pdata_id(u_id)
        if not entry:
            raise ValueError("Player not found")

        u_id, _, _, data = entry
        if payment_uuid in data.payments_uuid:
            data.payments_uuid.remove(payment_uuid)
            cls._update_blob(u_id, data)

    @classmethod
    def _update_blob(cls, u_id: int, data: PlayerData) -> None:
        blob = pickle.dumps(data)
        with cls._connect() as con:
            con.execute("UPDATE player_unit SET data = ? WHERE id = ?", (blob, u_id))
            con.commit()
