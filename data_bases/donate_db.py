import pickle
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntFlag

from .base_db import BaseDB


class DonateStatus(IntFlag):
    ACTIVE = 1 << 0  # Текуще активная
    INACTIVE = 1 << 1  # Неактивна
    HIDDEN = 1 << 2  # Скрыта
    ARCHIVED = 1 << 3  # Архивная запись (устаревшая)
    NO_STOCK = 1 << 4  # Распродано


@dataclass
class DonateMeta:
    name: str = ""
    description: str = ""

    limit: int | None = None

    price_main: Decimal = Decimal(0)
    sell_time_end: datetime | None = None

    _discount: int = 0
    _discount_time_end: datetime | None = None

    @property
    def price(self) -> Decimal:
        if self._discount <= 0:
            return self.price_main

        if self._discount >= 100:
            return Decimal(0)

        return self.price_main * (Decimal(100 - self._discount) / Decimal(100))

    def set_discount(self, discount: int, time_end: datetime | None) -> None:
        if discount > 100 or discount < 0:
            raise ValueError("discount bound 0-100")

        if time_end and time_end <= datetime.now():
            raise ValueError("time_end established in the past")

        self._discount = discount
        self._discount_time_end = time_end

    def recalculate_discount(self) -> None:
        if self._discount_time_end is None or self._discount_time_end >= datetime.now():
            return

        self._discount = 0
        self._discount_time_end = None

    def is_available(self) -> bool:
        if self.sell_time_end and self.sell_time_end < datetime.now():
            return False

        if self.limit is not None and self.limit <= 0:
            return False

        return True


class DonateDB(BaseDB):
    _db_name = "donate"

    @classmethod
    def pack_meta(cls, data: DonateMeta) -> bytes:
        return pickle.dumps(data)

    @classmethod
    def unpack_meta(cls, data: bytes) -> DonateMeta:
        try:
            return pickle.loads(data)

        except Exception:
            return DonateMeta()

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()

        with cls._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    meta BLOB,
                    status INTEGER NOT NULL
                );
            """)
            con.commit()

    @classmethod
    def get_donates(cls, status: DonateStatus) -> list[dict]:
        with cls._connect() as con:
            cur = con.execute(
                "SELECT * FROM services WHERE (status & ?) != 0", (status,)
            )
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "meta": cls.unpack_meta(row[1]),
                "status": DonateStatus(row[2]),
            }
            for row in rows
        ]
