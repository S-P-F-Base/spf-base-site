import pickle
import sqlite3
import uuid
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.parse import urlencode

from .config import Config


# region Statuses
class PaymentStatus(Enum):
    pending = 0
    done = 1
    cancel = 2


class PaymentCancelReason(Enum):
    none = 0
    check_incorrect = 1
    refund = 2


# endregion


class PaymentData:
    def __init__(
        self,
        amount: float,
        status: PaymentStatus,
        buyer: int,
        quantity: int,
        what_buy: int,
        cancel_reason: PaymentCancelReason = PaymentCancelReason.none,
        bd_id: int | None = None,
        fns_check_id: str | None = None,
        received: float = 0,
        user_pay: float = 0,
    ) -> None:
        # Немного говна с id для фнс и себя
        self._bd_id: int | None = bd_id
        self._fns_check_id: str | None = fns_check_id

        # Считаем денюшки
        self._amount: float = round(amount, 2)  # Сколько нужно
        self._received: float = round(received, 2)  # Сколько получили
        self._user_pay: float = round(user_pay, 2)  # Сколько юзер заплатил

        # Статусы
        self._status: PaymentStatus = status
        self._cancel_reason: PaymentCancelReason = cancel_reason

        # Информация о покупке
        self._buyer: int = buyer  # id from player db
        self._quantity: int = quantity
        self._what_buy: int = what_buy  # id form goods db

    # region geters
    @property
    def db_id(self) -> int | None:
        return self._bd_id

    @property
    def fns_check_id(self) -> str | None:
        return self._fns_check_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def received(self) -> float:
        return self._received

    @property
    def user_pay(self) -> float:
        return self._user_pay

    @property
    def status(self) -> PaymentStatus:
        return self._status

    @property
    def cancel_reason(self) -> PaymentCancelReason:
        return self._cancel_reason

    @property
    def buyer(self) -> int:
        return self._buyer

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def what_buy(self) -> int:
        return self._what_buy

    # endregion

    # region seters
    @fns_check_id.setter
    def fns_check_id(self, value: str | None) -> None:
        self._fns_check_id = value

    @amount.setter
    def amount(self, value: float) -> None:
        self._amount = round(value, 2)

    @received.setter
    def received(self, value: float) -> None:
        self._received = round(value, 2)

    @user_pay.setter
    def user_pay(self, value: float) -> None:
        self._user_pay = round(value, 2)

    @status.setter
    def status(self, value: PaymentStatus) -> None:
        self._status = value

    @cancel_reason.setter
    def cancel_reason(self, value: PaymentCancelReason) -> None:
        self._cancel_reason = value

    @buyer.setter
    def buyer(self, value: int) -> None:
        self._buyer = value

    @quantity.setter
    def quantity(self, value: int) -> None:
        self._quantity = value

    @what_buy.setter
    def what_buy(self, value: int) -> None:
        self._what_buy = value

    # endregion

    # region status
    def is_complete(self) -> bool:
        return self._status == PaymentStatus.done

    def is_cancel(self) -> bool:
        return self._status == PaymentStatus.cancel

    def update_status(self) -> None:
        if self._status == PaymentStatus.cancel:
            return

        if YoomoneyDB.USER_PAYS_COMMISSION:
            if self._amount >= self._received:
                self._status = PaymentStatus.done

        else:
            if self._amount >= self._user_pay:
                self._status = PaymentStatus.done

    # endregion

    # region serialize/deserialize
    def __getstate__(self):
        state = self.__dict__.copy()
        if "_bd_id" in state:
            del state["_bd_id"]

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(bd_id: int, data: bytes) -> "PaymentData":
        obj: PaymentData = pickle.loads(data)
        obj._bd_id = bd_id
        return obj

    # endregion


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
    def price_calculation_by_payment(
        cls,
        obj: PaymentData,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> float:
        if cls.USER_PAYS_COMMISSION:
            return cls.price_calculation(obj.amount - obj.received, payment_type)
        else:
            return cls.price_calculation(obj.amount - obj.user_pay, payment_type)

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
