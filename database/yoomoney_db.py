import sqlite3
import uuid
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.parse import urlencode

from .config import Config


class PaymentStatus(Enum):
    pending = 0
    done = 1
    cancel = 2
    not_enough = 3


class YoomoneyDB:
    _db_path = Path("data/payment.db")
    _lock = Lock()
    _commission_rates = {
        "PC": 0.01,  # Yoomoney
        "AC": 0.03,  # Банковская карта
    }
    USER_PAYS_COMMISSION: bool = False

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

        with (
            cls._connect() as con
        ):  # Необходимо id товара и кол-во сколько отправил сам пользователь
            con.executescript("""
                CREATE TABLE IF NOT EXISTS payment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    amount REAL NOT NULL,
                    receive REAL NOT NULL DEFAULT 0,
                    status INTEGER NOT NULL DEFAULT 0,
                    created DATETIME,
                    updated DATETIME
                );
                
                CREATE TABLE IF NOT EXISTS payment_links (
                    uuid TEXT PRIMARY KEY,
                    payment_id INTEGER NOT NULL,
                    created DATETIME,
                    FOREIGN KEY (payment_id) REFERENCES payment(id)
                )
            """)
            con.commit()

    @classmethod
    def create_payment(cls, user: str, amount: float) -> int:
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO payment (user, amount, created, updated)
                VALUES (?, ?, datetime('now'), datetime('now'))
            """,
                (user, amount),
            )
            con.commit()

            if cur.lastrowid is None:
                raise RuntimeError("Payment creation failed: lastrowid is None.")

            return cur.lastrowid

    @classmethod
    def update_payment(
        cls,
        id: int,
        status: PaymentStatus | Literal["auto"],
        receive: float,
        type_of_receive: Literal["add", "set"],
    ) -> bool:
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT amount, receive, status FROM payment WHERE id = ?", (id,)
            )
            row = cur.fetchone()

            if row is None:
                return False

            amount_db, receive_db, status_db = row

            if type_of_receive == "add":
                new_receive = receive_db + receive
            elif type_of_receive == "set":
                new_receive = receive
            else:
                raise ValueError("Invalid type_of_receive, must be 'add' or 'set'")

            if status == "auto":
                if status_db == PaymentStatus.cancel.value:
                    new_status = status_db
                else:
                    if new_receive >= amount_db:
                        new_status = PaymentStatus.done.value
                    elif new_receive > 0:
                        new_status = PaymentStatus.not_enough.value
                    else:
                        new_status = PaymentStatus.pending.value
            else:
                new_status = status.value

            cur.execute(
                """
                UPDATE payment
                SET status = ?, receive = ?, updated = datetime('now')
                WHERE id = ?
                """,
                (new_status, new_receive, id),
            )
            con.commit()

            return cur.rowcount > 0

    @classmethod
    def get_payments_by_id_range(cls, start_id: int, end_id: int) -> list[dict]:
        """
        Вернёт список платежей с id в диапазоне [start_id, end_id].
        Каждый платеж — словарь с полями из таблицы.
        """
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT id, user, amount, receive, status, created, updated
                FROM payment
                WHERE id BETWEEN ? AND ?
                ORDER BY id ASC
                """,
                (start_id, end_id),
            )
            rows = cur.fetchall()

            payments = []
            for row in rows:
                payments.append(
                    {
                        "id": row[0],
                        "user": row[1],
                        "amount": row[2],
                        "receive": row[3],
                        "status": PaymentStatus(row[4]),
                        "created": row[5],
                        "updated": row[6],
                    }
                )
            return payments

    @classmethod
    def get_payment_by_id(cls, payment_id: int) -> dict | None:
        with cls._connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT id, user, amount, receive, status, created, updated
                FROM payment
                WHERE id = ?
                """,
                (payment_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "user": row[1],
                "amount": row[2],
                "receive": row[3],
                "status": PaymentStatus(row[4]),
                "created": row[5],
                "updated": row[6],
            }

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

    @classmethod
    def price_calculation(
        cls,
        amount: float,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> float:
        sum_to_pay = amount

        if cls.USER_PAYS_COMMISSION:
            commission = cls._commission_rates[payment_type]
            match payment_type:
                case "PC":
                    sum_to_pay = amount / (1 - commission / (1 + commission))

                case "AC":
                    sum_to_pay = amount / (1 - commission)

                case _:
                    raise ValueError("Unknown type of payment_type")

        return round(sum_to_pay, 2)

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
