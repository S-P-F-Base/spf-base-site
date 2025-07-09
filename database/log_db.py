import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from threading import Lock


class LogType(Enum):
    LOGIN = 1
    LOGOUT = 2
    CREATE_USER = 3
    DELETE_USER = 4
    UPDATE_USER = 5


class LogDB:
    _db_path = Path("data/log.db")
    _lock = Lock()

    @classmethod
    @contextmanager
    def _connect(cls):
        with cls._lock:
            conn = sqlite3.connect(cls._db_path)
            try:
                yield conn
            finally:
                conn.close()

    @classmethod
    def create_db_table(cls) -> None:
        Path("data").mkdir(parents=True, exist_ok=True)

        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS log_unit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type INTEGER NOT NULL,
                    time INTEGER NOT NULL,
                    value TEXT NOT NULL,
                    creator TEXT NOT NULL
                )
            """)
            con.commit()

    @classmethod
    def add_log(
        cls,
        log_type: LogType,
        value: str,
        creator: str,
        time: datetime | None = None,
    ) -> None:
        if time:
            now_ts = int(time.timestamp())
        else:
            now_ts = int(datetime.now(UTC).timestamp())

        with cls._connect() as con:
            con.execute(
                "INSERT INTO log_unit (type, time, value, creator) VALUES (?, ?, ?, ?)",
                (log_type.value, now_ts, value, creator),
            )
            con.commit()
