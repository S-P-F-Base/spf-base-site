from enum import IntFlag

from .base_db import BaseDB


class DonateStatus(IntFlag):
    ACTIVE = 1 << 0  # Текуще активная
    INACTIVE = 1 << 1  # Неактивна
    HIDDEN = 1 << 2  # Скрыта
    ARCHIVED = 1 << 3  # Архивная запись (устаревшая)
    NO_STOCK = 1 << 4  # Распродано


class DonateDB(BaseDB):
    _db_name = "donate"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()

        with cls._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    price TEXT,
                    discount INTEGER,
                    meta BLOB,
                    status INTEGER NOT NULL
                );
            """)
            con.commit()
