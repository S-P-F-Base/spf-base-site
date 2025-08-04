from datetime import datetime, timedelta, timezone
from typing import Literal

from requests import Session

from .config import Config


class AutoTax:
    _tax_session: Session = Session()

    @classmethod
    def _base_url(cls, parms: str = "") -> str:
        return f"https://lknpd.nalog.ru/api/v1/{parms}"

    @classmethod
    def _get_cur_time(cls) -> str:
        return (
            datetime.now(timezone(timedelta(hours=3)))
            .replace(microsecond=0)
            .isoformat()
        )

    @classmethod
    def setup(cls) -> None:
        return

        # TODO: Сделать нормальную работу с этой хуетой

        cls._tax_session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Authorization": Config.tax_authorization(),
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
            }
        )

    @classmethod
    def post_income(cls, services: list[tuple[str, float]]) -> str:
        time = cls._get_cur_time()

        rounded_services = [
            {
                "name": name,
                "amount": round(amount, 2),
                "quantity": 1,  # Брух ФНС
            }
            for name, amount in services
        ]

        total = round(sum(item["amount"] for item in rounded_services), 2)

        payload = {
            "operationTime": time,
            "requestTime": time,
            "services": rounded_services,
            "totalAmount": f"{total:.2f}",
            "client": {
                "contactPhone": None,
                "displayName": None,
                "inn": None,
                "incomeType": "FROM_INDIVIDUAL",
            },
            "paymentType": "CASH",
            "ignoreMaxTotalIncomeRestriction": False,
        }

        response = cls._tax_session.post(cls._base_url("income"), json=payload)

        if not response.ok:
            raise RuntimeError(
                f"Invalid response from post_income: {response.status_code} {response.text}"
            )

        uuid = response.json().get("approvedReceiptUuid", None)
        if not uuid:
            raise RuntimeError("approvedReceiptUuid missing in response")

        return uuid

    @classmethod
    def post_cancel(
        cls,
        uuid: str,
        reason: Literal["Чек сформирован ошибочно", "Возврат средств"],
    ) -> bool:
        time = cls._get_cur_time()

        payload = {
            "operationTime": time,
            "requestTime": time,
            "comment": reason,
            "receiptUuid": uuid,
            "partnerCode": None,
        }

        response = cls._tax_session.post(cls._base_url("cancel"), json=payload)

        if not response.ok:
            raise RuntimeError(
                f"Invalid response from post_cancel: {response.status_code} {response.text}"
            )

        return True

    @classmethod
    def get_check_png(cls, uuid: str) -> bytes:
        response = cls._tax_session.get(
            cls._base_url(f"receipt/{Config.tax_inn()}/{uuid}/print")
        )

        if not response.ok:
            raise RuntimeError(
                f"Invalid response from get_check_png: {response.status_code} {response.text}"
            )

        return response.content
