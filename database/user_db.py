import sqlite3
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Final

import bcrypt

from .log_db import LogDB, LogType


# НЕ ИСПОЛЬЗОВАТЬ БИТЫ ВЫШЕ 1 << 62!
class UserAccess(Enum):
    NO_ACCESS = 0
    ALL_ACCESS = 1 << 0

    READ_USER = 1 << 1
    CONTROL_USER = 1 << 2

    READ_GAME_SERVER = 1 << 3
    CONTROL_GAME_SERVER = 1 << 4

    READ_PAYMENT = 1 << 5
    GIVE_PAYMENT = 1 << 6
    CONTROL_PAYMENT = 1 << 7

    READ_PLAYER = 1 << 8
    CONTROL_PLAYER = 1 << 9

    READ_LOGS = 1 << 10
    CONTROL_LOGS = 1 << 11


class UserDB:
    system_user: Final[str] = "System"
    _db_path = Path("data/user.db")
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
    def _has_user(cls, login: str, con: sqlite3.Connection) -> bool:
        return (
            con.execute("SELECT 1 FROM user_unit WHERE login = ?", (login,)).fetchone()
            is not None
        )

    @classmethod
    def create_db_table(cls) -> None:
        Path("data").mkdir(parents=True, exist_ok=True)

        with cls._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS user_unit (
                    login TEXT PRIMARY KEY,
                    password BLOB NOT NULL,
                    access INTEGER NOT NULL
                )
            """)

    @classmethod
    def _hash_password(cls, password: str) -> bytes:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    @classmethod
    def check_password(cls, login: str, password: str) -> bool:
        with cls._connect() as con:
            cur = con.execute(
                "SELECT password FROM user_unit WHERE login = ?", (login,)
            )
            row = cur.fetchone()
            if row is None:
                return False

        return bcrypt.checkpw(password.encode(), row[0])

    @classmethod
    def has_access(cls, login: str, required_access: int) -> bool:
        with cls._connect() as con:
            cur = con.execute("SELECT access FROM user_unit WHERE login = ?", (login,))
            row = cur.fetchone()
            if row is None:
                return False

            user_access = row[0]

        if user_access & UserAccess.ALL_ACCESS.value:
            return True

        return (user_access & required_access) == required_access

    @classmethod
    def create_user(cls, login: str, password: str, creator: str) -> None:
        if len(password.encode()) > 72:
            raise ValueError("Password too long for bcrypt (max 72 bytes)")

        with cls._connect() as con:
            if cls._has_user(login, con):
                raise ValueError("User already exists")

            hashed = cls._hash_password(password)
            con.execute(
                "INSERT INTO user_unit (login, password, access) VALUES (?, ?, ?)",
                (login, hashed, UserAccess.NO_ACCESS.value),
            )
            con.commit()

        LogDB.add_log(LogType.CREATE_USER, f"Created user {login}", creator)

    @classmethod
    def set_user_access(cls, login: str, access: int, creator: str) -> None:
        with cls._connect() as con:
            if not cls._has_user(login, con):
                raise ValueError("User doesn't exist")

            con.execute(
                "UPDATE user_unit SET access = ? WHERE login = ?", (access, login)
            )
            con.commit()

        LogDB.add_log(
            LogType.UPDATE_USER,
            f"User '{login}' access updated to {access}",
            creator,
        )

    @classmethod
    def delete_user(cls, login: str, creator: str) -> None:
        with cls._connect() as con:
            if not cls._has_user(login, con):
                raise ValueError("User doesn't exist")

            con.execute("DELETE FROM user_unit WHERE login = ?", (login,))
            con.commit()

        LogDB.add_log(LogType.DELETE_USER, f"Deleted user {login}", creator)

    @classmethod
    def user_exists(cls, login: str) -> bool:
        with cls._connect() as con:
            return cls._has_user(login, con)

    @classmethod
    def get_user_access(cls, login: str) -> int | None:
        with cls._connect() as con:
            cur = con.execute("SELECT access FROM user_unit WHERE login = ?", (login,))
            row = cur.fetchone()
            if row is None:
                return None

            return row[0]

    @classmethod
    def get_all_users(cls) -> list[str]:
        with cls._connect() as con:
            cur = con.execute("SELECT login FROM user_unit")
            return [row[0] for row in cur.fetchall()]
