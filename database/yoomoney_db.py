import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.parse import urlencode

from .config import Config
from .payment_datatype import PaymentData


class YoomoneyDB:
    _db_path = Path("data/yoomoney.db")
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
            con.executescript("""
                CREATE TABLE IF NOT EXISTS payment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data BLOB NOT NULL 
                );
                
                CREATE TABLE IF NOT EXISTS payment_links (
                    uuid TEXT PRIMARY KEY,
                    payment_id INTEGER NOT NULL,
                    created DATETIME,
                    FOREIGN KEY (payment_id) REFERENCES payment(id)
                )
            """)
            con.commit()

    # region Redirect
    @classmethod
    def create_payment_link(cls, payment_id: int) -> str:
        link_uuid = str(uuid.uuid4())
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO payment_links (uuid, payment_id, created) VALUES (?, ?, datetime('now'))",
                (link_uuid, payment_id),
            )
            con.commit()
        return link_uuid

    @classmethod
    def resolve_payment_id_by_uuid(cls, uuid_str: str) -> int | None:
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT payment_id FROM payment_links WHERE uuid = ?", (uuid_str,)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            return None

    # endregion

    # region Yoomoney etc

    @classmethod
    def generate_yoomoney_payment_url(
        cls,
        amount: float,
        successURL: str,
        label: str,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> str:
        params = {
            "receiver": Config.yoomoney_account(),
            "quickpay-form": "button",
            "paymentType": payment_type,
            "sum": amount,
            "label": label,
            "successURL": successURL,
        }
        return f"https://yoomoney.ru/quickpay/confirm?{urlencode(params)}"

    # endregion

    # region payment
    @classmethod
    def get_payment(cls, payment_id: int) -> PaymentData | None:
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute("SELECT data FROM payment WHERE id = ?", (payment_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return PaymentData.deserialize(payment_id, row[0])

    @classmethod
    def set_payment(cls, payment: PaymentData) -> None:
        if payment.db_id is None:
            raise ValueError("Payment havent db_id — use append instead")

        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE payment SET data = ? WHERE id = ?",
                (payment.serialize(), payment.db_id),
            )
            con.commit()

    @classmethod
    def append_payment(cls, payment: PaymentData) -> int:
        if payment.db_id is not None:
            raise ValueError("Payment already has db_id — use set instead")

        with cls._connect() as con:
            cur = con.cursor()
            cur.execute("SELECT MAX(id) FROM payment")
            row = cur.fetchone()
            next_id = (row[0] or 0) + 1

            payment._bd_id = next_id

            cur.execute(
                "INSERT INTO payment (id, data) VALUES (?, ?)",
                (next_id, payment.serialize()),
            )
            con.commit()

        return next_id

    # endregion
