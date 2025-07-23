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

    PAY_CREATE = 6
    PAY_UPDATE = 7
    PAY_RESIVE = 8
    PAY_CANSEL = 9

    GAME_SERVER_START = 10
    GAME_SERVER_STOP = 11


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

    @classmethod
    def get_min_max_log_id(cls) -> tuple[int | None, int | None]:
        with cls._connect() as con:
            cur = con.execute("SELECT MIN(id), MAX(id) FROM log_unit")
            row = cur.fetchone()
            if row:
                return row[0], row[1]
            return None, None

    @classmethod
    def get_logs_range(cls, start_id: int, end_id: int) -> list[dict]:
        with cls._connect() as con:
            cur = con.execute(
                "SELECT id, type, time, value, creator FROM log_unit WHERE id BETWEEN ? AND ? ORDER BY id ASC",
                (start_id, end_id),
            )
            rows = cur.fetchall()

        logs = []
        for row in rows:
            log = {
                "id": row[0],
                "type": LogType(row[1]),
                "time": datetime.fromtimestamp(row[2], tz=UTC),
                "value": row[3],
                "creator": row[4],
            }
            logs.append(log)

        return logs

    @classmethod
    def get_logs_by_creator(cls, creator: str) -> list[dict]:
        with cls._connect() as con:
            cur = con.execute(
                "SELECT id, type, time, value, creator FROM log_unit WHERE creator = ? ORDER BY time ASC",
                (creator,),
            )
            rows = cur.fetchall()

        logs = []
        for row in rows:
            log = {
                "id": row[0],
                "type": LogType(row[1]),
                "time": datetime.fromtimestamp(row[2], tz=UTC),
                "value": row[3],
                "creator": row[4],
            }
            logs.append(log)

        return logs

    @classmethod
    def get_logs_by_time_range(
        cls, start_time: datetime, end_time: datetime
    ) -> list[dict]:
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        with cls._connect() as con:
            cur = con.execute(
                "SELECT id, type, time, value, creator FROM log_unit WHERE time BETWEEN ? AND ? ORDER BY time ASC",
                (start_ts, end_ts),
            )
            rows = cur.fetchall()

        logs = []
        for row in rows:
            log = {
                "id": row[0],
                "type": LogType(row[1]),
                "time": datetime.fromtimestamp(row[2], tz=UTC),
                "value": row[3],
                "creator": row[4],
            }
            logs.append(log)

        return logs
