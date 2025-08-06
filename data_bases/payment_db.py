import pickle
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, IntFlag
from typing import Literal
from urllib.parse import urlencode

from data_control.config import Config

from .base_db import BaseDB


# region service classes
class ServiceStatus(IntFlag):
    ACTIVE = 1 << 0  # Текуще активная
    INACTIVE = 1 << 1  # Неактивна
    HIDDEN = 1 << 2  # Скрыта
    ARCHIVED = 1 << 3  # Архивная запись (устаревшая)
    NO_STOCK = 1 << 4  # Распродано


@dataclass
class ServiceMeta:
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

    # region serialize/deserialize
    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(data: bytes) -> "ServiceMeta":
        return pickle.loads(data)

    # endregion


# endregion

# region payment datatype


class PaymentStatus(Enum):
    pending = 0
    done = 1
    cancel = 2


class PaymentCancelReason(Enum):
    none = 0
    check_incorrect = 1
    refund = 2


class PaymentData:
    def __init__(
        self,
        amount: Decimal,
        status: PaymentStatus,
        buyer: str,
        quantity: int,
        what_buy: str,
        cancel_reason: PaymentCancelReason = PaymentCancelReason.none,
        tax_check_id: str | None = None,
        received: Decimal = Decimal("0"),
        user_pay: Decimal = Decimal("0"),
    ) -> None:
        # Немного говна с id для фнс и себя
        self._tax_check_id: str | None = tax_check_id

        # Считаем денюшки
        self._amount = amount.quantize(Decimal("0.01"))  # Сколько нужно
        self._received = received.quantize(Decimal("0.01"))  # Сколько получили
        self._user_pay = user_pay.quantize(Decimal("0.01"))  # Сколько юзер заплатил

        # Статусы
        self._status: PaymentStatus = status
        self._cancel_reason: PaymentCancelReason = cancel_reason

        # Информация о покупке
        self._buyer: str = buyer  # uuid from player db
        self._quantity: int = quantity
        self._what_buy: str = what_buy  # uuid form services table

    # region geters
    @property
    def tax_check_id(self) -> str | None:
        return self._tax_check_id

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def received(self) -> Decimal:
        return self._received

    @property
    def user_pay(self) -> Decimal:
        return self._user_pay

    @property
    def status(self) -> PaymentStatus:
        return self._status

    @property
    def cancel_reason(self) -> PaymentCancelReason:
        return self._cancel_reason

    @property
    def buyer(self) -> str:
        return self._buyer

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def what_buy(self) -> str:
        return self._what_buy

    # endregion

    # region seters
    @tax_check_id.setter
    def tax_check_id(self, value: str | None) -> None:
        self._tax_check_id = value

    @amount.setter
    def amount(self, value: Decimal) -> None:
        self._amount = value.quantize(Decimal("0.01"))

    @received.setter
    def received(self, value: Decimal) -> None:
        self._received = value.quantize(Decimal("0.01"))

    @user_pay.setter
    def user_pay(self, value: Decimal) -> None:
        self._user_pay = value.quantize(Decimal("0.01"))

    @status.setter
    def status(self, value: PaymentStatus) -> None:
        self._status = value

    @cancel_reason.setter
    def cancel_reason(self, value: PaymentCancelReason) -> None:
        self._cancel_reason = value

    @buyer.setter
    def buyer(self, value: str) -> None:
        self._buyer = value

    @quantity.setter
    def quantity(self, value: int) -> None:
        self._quantity = value

    @what_buy.setter
    def what_buy(self, value: str) -> None:
        self._what_buy = value

    # endregion

    # region status
    def is_complete(self) -> bool:
        return self._status == PaymentStatus.done

    def is_cancel(self) -> bool:
        return self._status == PaymentStatus.cancel

    def update_status(self) -> PaymentStatus:
        if self._status == PaymentStatus.cancel:
            return self._status

        if Config.user_pays_commission():
            if self._amount >= self._received:
                self._status = PaymentStatus.done

        else:
            if self._amount >= self._user_pay:
                self._status = PaymentStatus.done

        return self._status

    # endregion

    # region serialize/deserialize
    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(data: bytes) -> "PaymentData":
        return pickle.loads(data)

    # endregion

    # region price
    @staticmethod
    def price_calculation(
        amount: Decimal,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> Decimal:
        sum_to_pay = amount

        if Config.user_pays_commission():
            commission = Decimal(str(Config.get_commission_rates(payment_type)))
            match payment_type:
                case "PC":
                    sum_to_pay = amount / (
                        Decimal("1") - commission / (Decimal("1") + commission)
                    )

                case "AC":
                    sum_to_pay = amount / (Decimal("1") - commission)

                case _:
                    raise ValueError("Unknown type of payment_type")

        return sum_to_pay.quantize(Decimal("0.01"))

    def price_calculation_by_payment(
        self,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> Decimal:
        if Config.user_pays_commission():
            return self.price_calculation(self.amount - self.received, payment_type)

        else:
            return self.price_calculation(self.amount - self.user_pay, payment_type)

    # endregion


# endregion


class PaymentDB(BaseDB):
    _db_name = "payment"

    @classmethod
    def has_exist_u_id(
        cls,
        u_id: str,
        table: Literal["services", "payments", "payments_links"],
    ) -> bool:
        if table not in {"services", "payments", "payments_links"}:
            raise ValueError("Invalid table name")

        with cls._connect() as con:
            cur = con.execute(f"SELECT 1 FROM {table} WHERE uuid = ?", (u_id,))
            return cur.fetchone() is not None

    @classmethod
    def gen_valid_u_id(
        cls,
        table: Literal["services", "payments", "payments_links"],
    ) -> str:
        if table not in {"services", "payments", "payments_links"}:
            raise ValueError("Invalid table name")

        for _ in range(10):
            u_id = uuid.uuid4().hex
            with cls._connect() as con:
                cur = con.execute(f"SELECT 1 FROM {table} WHERE uuid = ?", (u_id,))
                if not cur.fetchone():
                    return u_id

        raise RuntimeError("Failed to generate unique UUID after 10 attempts")

    @classmethod
    def generate_yoomoney_payment_url(
        cls,
        amount: Decimal,
        successURL: str,
        label: str,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> str:
        params = {
            "receiver": Config.yoomoney_account(),
            "quickpay-form": "button",
            "paymentType": payment_type,
            "sum": str(amount),
            "label": label,
            "successURL": successURL,
        }
        return f"https://yoomoney.ru/quickpay/confirm?{urlencode(params)}"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()

        with cls._connect() as con:
            con.executescript("""
                -- Для всех услуг которые когда либо были
                CREATE TABLE IF NOT EXISTS services (
                    uuid TEXT PRIMARY KEY,
                    status INTEGER NOT NULL,
                    meta BLOB NOT NULL
                );
                
                -- Для обработки платежей
                CREATE TABLE IF NOT EXISTS payments (
                    uuid TEXT PRIMARY KEY,
                    data BLOB NOT NULL
                );
                
                -- Для редиректа платежей
                CREATE TABLE IF NOT EXISTS payments_links (
                    uuid TEXT PRIMARY KEY,
                    payment_uuid TEXT NOT NULL,
                    created DATETIME,
                    FOREIGN KEY (payment_uuid) REFERENCES payments(uuid)
                )
            """)
            con.commit()

    class services:
        @classmethod
        def append(
            cls,
            meta: ServiceMeta,
            status: ServiceStatus,
        ) -> str:
            u_id = PaymentDB.gen_valid_u_id("services")
            meta_blob = meta.serialize()

            with PaymentDB._connect() as con:
                con.execute(
                    "INSERT INTO services (uuid, status, meta) VALUES (?, ?, ?)",
                    (u_id, status, meta_blob),
                )
                con.commit()

            return u_id

        @classmethod
        def edit(
            cls,
            u_id: str,
            meta: ServiceMeta,
            status: ServiceStatus,
        ) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "services"):
                raise ValueError("UUID does not exist")

            meta_blob = meta.serialize()

            with PaymentDB._connect() as con:
                cur = con.execute(
                    "UPDATE services SET status = ?, meta = ? WHERE uuid = ?",
                    (status, meta_blob, u_id),
                )
                con.commit()
                return cur.rowcount > 0

        @classmethod
        def delete(cls, u_id: str) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "services"):
                raise ValueError("UUID does not exist")

            with PaymentDB._connect() as con:
                cur = con.execute(
                    "DELETE FROM services WHERE uuid = ?",
                    (u_id,),
                )
                con.commit()

            return cur.rowcount > 0

        @classmethod
        def get_by_u_id(
            cls, u_id: str
        ) -> dict[str, str | ServiceMeta | ServiceStatus] | None:
            with PaymentDB._connect() as con:
                cur = con.execute("SELECT * FROM services WHERE uuid = ?", (u_id,))
                row = cur.fetchone()

            return (
                {
                    "uuid": row[0],
                    "status": ServiceStatus(row[1]),
                    "meta": ServiceMeta.deserialize(row[2]),
                }
                if row
                else None
            )

        @classmethod
        def get_by_status(cls, status: ServiceStatus) -> list[dict]:
            with PaymentDB._connect() as con:
                cur = con.execute(
                    "SELECT uuid, status, meta FROM services WHERE (status & ?) != 0",
                    (status,),
                )
                rows = cur.fetchall()

            return [
                {
                    "uuid": row[0],
                    "status": ServiceStatus(row[1]),
                    "meta": ServiceMeta.deserialize(row[2]),
                }
                for row in rows
            ]

        @classmethod
        def get_all(cls) -> list[dict]:
            with PaymentDB._connect() as con:
                cur = con.execute("SELECT uuid, status, meta FROM services")
                rows = cur.fetchall()

            return [
                {
                    "uuid": uuid,
                    "status": ServiceStatus(status),
                    "meta": ServiceMeta.deserialize(meta_blob),
                }
                for uuid, status, meta_blob in rows
            ]

    class payments:
        @classmethod
        def append(cls, value: PaymentData) -> str:
            u_id = PaymentDB.gen_valid_u_id("payments")
            data_blob = value.serialize()
            with PaymentDB._connect() as con:
                con.execute(
                    "INSERT INTO payments (uuid, data) VALUES (?, ?)",
                    (u_id, data_blob),
                )
                con.commit()

            return u_id

        @classmethod
        def edit(cls, u_id: str, value: PaymentData) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "payments"):
                raise ValueError("UUID does not exist")

            data_blob = value.serialize()
            with PaymentDB._connect() as con:
                cur = con.execute(
                    "UPDATE payments SET data = ? WHERE uuid = ?",
                    (data_blob, u_id),
                )
                con.commit()

            return cur.rowcount > 0

        @classmethod
        def delete(cls, u_id: str) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "payments"):
                raise ValueError("UUID does not exist")

            with PaymentDB._connect() as con:
                cur = con.execute("DELETE FROM payments WHERE uuid = ?", (u_id,))
                con.commit()

            return cur.rowcount > 0

        @classmethod
        def get_by_u_id(cls, u_id: str) -> PaymentData | None:
            with PaymentDB._connect() as con:
                cur = con.execute("SELECT data FROM payments WHERE uuid = ?", (u_id,))
                row = cur.fetchone()

            if not row:
                return None

            return PaymentData.deserialize(row[0])

        @classmethod
        def get_all(cls) -> list[dict]:
            with PaymentDB._connect() as con:
                cur = con.execute("SELECT uuid, data FROM payments")
                rows = cur.fetchall()

            return [
                {
                    "uuid": uuid,
                    "data": PaymentData.deserialize(data_blob),
                }
                for uuid, data_blob in rows
            ]

    class payments_links:
        @classmethod
        def append(cls, payment_id: str) -> str:
            u_id = PaymentDB.gen_valid_u_id("payments_links")
            created = datetime.now()
            with PaymentDB._connect() as con:
                con.execute(
                    "INSERT INTO payments_links (uuid, payment_uuid, created) VALUES (?, ?, ?)",
                    (u_id, payment_id, created),
                )
                con.commit()

            return u_id

        @classmethod
        def edit(cls, u_id: str, new_payment_id: str) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "payments_links"):
                raise ValueError("UUID does not exist")

            with PaymentDB._connect() as con:
                cur = con.execute(
                    "UPDATE payments_links SET payment_uuid = ? WHERE uuid = ?",
                    (new_payment_id, u_id),
                )
                con.commit()

            return cur.rowcount > 0

        @classmethod
        def delete(cls, u_id: str) -> bool:
            if not PaymentDB.has_exist_u_id(u_id, "payments_links"):
                raise ValueError("UUID does not exist")

            with PaymentDB._connect() as con:
                cur = con.execute("DELETE FROM payments_links WHERE uuid = ?", (u_id,))
                con.commit()

            return cur.rowcount > 0

        @classmethod
        def get_by_u_id(cls, u_id: str) -> dict | None:
            with PaymentDB._connect() as con:
                cur = con.execute(
                    "SELECT payment_uuid, created FROM payments_links WHERE uuid = ?",
                    (u_id,),
                )
                row = cur.fetchone()

            if not row:
                return None

            return {
                "uuid": u_id,
                "payment_uuid": row[0],
                "created": row[1],
            }

        @classmethod
        def get_all(cls) -> list[dict]:
            with PaymentDB._connect() as con:
                cur = con.execute(
                    "SELECT uuid, payment_uuid, created FROM payments_links"
                )
                rows = cur.fetchall()

            return [
                {"uuid": uuid, "payment_uuid": p_id, "created": created}
                for uuid, p_id, created in rows
            ]
