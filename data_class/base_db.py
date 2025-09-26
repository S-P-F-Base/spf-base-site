import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock


class BaseDB:
    _db_name: str = ""
    _lock = Lock()

    @classmethod
    @contextmanager
    def _connect(cls):
        with cls._lock:
            conn = sqlite3.connect(Path("data/dbs_v2") / (cls._db_name + ".db"))
            try:
                yield conn

            finally:
                conn.close()

    @classmethod
    def create_db_dir(cls) -> None:
        Path("data/dbs_v2").mkdir(parents=True, exist_ok=True)
