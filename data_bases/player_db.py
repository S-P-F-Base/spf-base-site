import pickle
from dataclasses import dataclass

from .base_db import BaseDB


@dataclass
class PlayerData:
    discord_id: str
    discord_name: str
    steam_id: str
    payments_uuid: list[str]


class PlayerDB(BaseDB):
    _db_name = "player"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()

        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS player_unit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT NOT NULL,
                    discord_name TEXT,
                    steam_id TEXT NOT NULL,
                    payments_uuid BLOB
                )
            """)
            con.commit()

    @classmethod
    def add_player(cls, data: PlayerData) -> int | None:
        blob = pickle.dumps(data.payments_uuid)
        with cls._connect() as con:
            cur = con.execute(
                "INSERT INTO player_unit (discord_id, discord_name, steam_id, payments_uuid) VALUES (?, ?, ?, ?)",
                (data.discord_id, data.discord_name, data.steam_id, blob),
            )
            con.commit()
            return cur.lastrowid

    @classmethod
    def remove_player(cls, u_id: int) -> None:
        with cls._connect() as con:
            con.execute("DELETE FROM player_unit WHERE id = ?", (u_id,))
            con.commit()

    @classmethod
    def _row_to_data(cls, row: tuple) -> tuple[int, PlayerData]:
        u_id, discord_id, discord_name, steam_id, payments_blob = row
        payments_uuid = pickle.loads(payments_blob) if payments_blob else []
        return u_id, PlayerData(discord_id, discord_name, steam_id, payments_uuid)

    @classmethod
    def get_pdata_id(cls, u_id: int) -> tuple[int, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, discord_name, steam_id, payments_uuid FROM player_unit WHERE id = ?",
                (u_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_discord(cls, discord_id: str) -> tuple[int, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, discord_name, steam_id, payments_uuid FROM player_unit WHERE discord_id = ?",
                (discord_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_steam(cls, steam_id: str) -> tuple[int, PlayerData] | None:
        with cls._connect() as con:
            row = con.execute(
                "SELECT id, discord_id, discord_name, steam_id, payments_uuid FROM player_unit WHERE steam_id = ?",
                (steam_id,),
            ).fetchone()
            return cls._row_to_data(row) if row else None

    @classmethod
    def get_pdata_name(cls, name: str) -> list[tuple[int, PlayerData]]:
        with cls._connect() as con:
            rows = con.execute(
                "SELECT id, discord_id, discord_name, steam_id, payments_uuid FROM player_unit WHERE LOWER(discord_name) LIKE LOWER(?)",
                (f"%{name}%",),
            ).fetchall()
            return [cls._row_to_data(row) for row in rows]

    @classmethod
    def get_pdata_all(cls) -> list[tuple[int, PlayerData]]:
        with cls._connect() as con:
            rows = con.execute(
                "SELECT id, discord_id, discord_name, steam_id, payments_uuid FROM player_unit"
            ).fetchall()
            return [cls._row_to_data(row) for row in rows]

    @classmethod
    def add_payment(cls, u_id: int, payment_uuid: str) -> None:
        pdata = cls.get_pdata_id(u_id)
        if not pdata:
            raise ValueError("Player not found")

        _, data = pdata
        if payment_uuid not in data.payments_uuid:
            data.payments_uuid.append(payment_uuid)
            cls._update_payments_blob(u_id, data.payments_uuid)

    @classmethod
    def remove_payment(cls, u_id: int, payment_uuid: str) -> None:
        pdata = cls.get_pdata_id(u_id)
        if not pdata:
            raise ValueError("Player not found")

        _, data = pdata
        if payment_uuid in data.payments_uuid:
            data.payments_uuid.remove(payment_uuid)
            cls._update_payments_blob(u_id, data.payments_uuid)

    @classmethod
    def _update_payments_blob(cls, u_id: int, uuid_list: list[str]) -> None:
        blob = pickle.dumps(uuid_list)
        with cls._connect() as con:
            con.execute(
                "UPDATE player_unit SET payments_uuid = ? WHERE id = ?", (blob, u_id)
            )
            con.commit()
