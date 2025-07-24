import pickle
from enum import Enum
from typing import Literal

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
        tax_check_id: str | None = None,
        received: float = 0,
        user_pay: float = 0,
    ) -> None:
        # Немного говна с id для фнс и себя
        self._bd_id: int | None = bd_id
        self._tax_check_id: str | None = tax_check_id

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
    def tax_check_id(self) -> str | None:
        return self._tax_check_id

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
    @tax_check_id.setter
    def tax_check_id(self, value: str | None) -> None:
        self._tax_check_id = value

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

        if Config.user_pays_commission():
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

    # region price
    @staticmethod
    def price_calculation(
        amount: float,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> float:
        sum_to_pay = amount

        if Config.user_pays_commission():
            commission = Config.get_commission_rates(payment_type)
            match payment_type:
                case "PC":
                    sum_to_pay = amount / (1 - commission / (1 + commission))

                case "AC":
                    sum_to_pay = amount / (1 - commission)

                case _:
                    raise ValueError("Unknown type of payment_type")

        return round(sum_to_pay, 2)

    def price_calculation_by_payment(
        self,
        payment_type: Literal["PC", "AC"] = "AC",
    ) -> float:
        if Config.user_pays_commission():
            return self.price_calculation(self.amount - self.received, payment_type)
        else:
            return self.price_calculation(self.amount - self.user_pay, payment_type)

    # endregion

    # region resolve db id
    def get_buyer_info(self) -> dict: ...

    def get_what_buy_info(self) -> dict: ...

    # endregion
