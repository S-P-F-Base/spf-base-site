import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Final, Literal

from requests import Session

from .config import Config

TWOPLACES = Decimal("0.01")


class AutoTax:
    _tax_session: Session = Session()
    _device_id = ""
    _token_expire = ""
    _refresh_token = ""
    _user_agent: Final[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36"
    )

    @classmethod
    def _base_url(cls, parms: str = "") -> str:
        return f"https://lknpd.nalog.ru/api/v1/{parms}"

    @classmethod
    def req_get(cls, path: str, **kwargs):
        if cls._is_token_expired():
            logging.info("Token expired, refreshing...")
            cls._refresh()

        resp = cls._tax_session.get(cls._base_url(path), **kwargs)
        if not resp.ok:
            raise RuntimeError(f"GET {path} failed: {resp.status_code} {resp.text}")

        return resp

    @classmethod
    def req_post(cls, path: str, json=None, **kwargs):
        if cls._is_token_expired():
            logging.info("Token expired, refreshing...")
            cls._refresh()

        resp = cls._tax_session.post(cls._base_url(path), json=json, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"POST {path} failed: {resp.status_code} {resp.text}")

        return resp

    @classmethod
    def _is_token_expired(cls) -> bool:
        if not cls._token_expire:
            return True

        try:
            dt = datetime.fromisoformat(cls._token_expire.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) >= dt

        except Exception as e:
            logging.warning(f"Invalid tokenExpireIn format: {cls._token_expire} ({e})")
            return True

    @classmethod
    def _get_cur_time(cls) -> str:
        return (
            datetime.now(timezone(timedelta(hours=3)))
            .replace(microsecond=0)
            .isoformat()
        )

    @classmethod
    def _generate_source_device_id(cls, length: int = 21) -> str:
        raw_bytes = os.urandom(16)
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        cleaned = b64.replace("+", "").replace("/", "").replace("=", "")
        return cleaned[:length]

    @classmethod
    def _update_data(cls, data_json: dict) -> None:
        cls._token_expire = data_json.get("tokenExpireIn")
        cls._refresh_token = data_json.get("refreshToken")

        cls._tax_session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Authorization": data_json.get("token", ""),
                "User-Agent": cls._user_agent,
            }
        )

    @classmethod
    def _login(cls) -> None:
        cls._device_id = cls._generate_source_device_id()

        resp = cls._tax_session.post(
            cls._base_url("auth/lkfl"),
            json={
                "username": Config.tax_inn(),
                "password": Config.tax_password(),
                "deviceInfo": {
                    "sourceType": "WEB",
                    "appVersion": "1.0.0",
                    "sourceDeviceId": cls._device_id,
                    "metaDetails": {"userAgent": cls._user_agent},
                },
            },
        )

        if not resp.ok:
            logging.error(
                f"Error while login to lknpd.nalog.ru. Code: {resp.status_code}. Anser: {resp.text}"
            )
            return

        cls._update_data(resp.json())

    @classmethod
    def _refresh(cls) -> None:
        resp = cls._tax_session.post(
            cls._base_url("auth/token"),
            json={
                "refreshToken": cls._refresh_token,
                "deviceInfo": {
                    "sourceType": "WEB",
                    "appVersion": "1.0.0",
                    "sourceDeviceId": cls._device_id,
                    "metaDetails": {"userAgent": cls._user_agent},
                },
            },
        )

        if not resp.ok:
            logging.error(
                f"Error while refresh token from lknpd.nalog.ru. Code: {resp.status_code}. Anser: {resp.text}"
            )
            return

        cls._update_data(resp.json())

    @classmethod
    def setup(cls) -> None:
        cls._login()

    @classmethod
    def post_income(cls, services: list[tuple[str, Decimal]]) -> str:
        if not services:
            raise ValueError("Services list is empty")

        time = cls._get_cur_time()

        items_dec = [
            {
                "name": name,
                "amount_dec": Decimal(amount).quantize(TWOPLACES, ROUND_HALF_UP),
                "quantity": 1,
            }
            for name, amount in services
        ]

        if any(i["amount_dec"] <= 0 for i in items_dec):
            raise ValueError("All service amounts must be > 0")

        total_dec = sum((i["amount_dec"] for i in items_dec), Decimal("0.00")).quantize(
            TWOPLACES, ROUND_HALF_UP
        )

        rounded_services = [
            {
                "name": i["name"],
                "amount": f"{i['amount_dec']:.2f}",
                "quantity": i["quantity"],
            }
            for i in items_dec
        ]

        payload = {
            "operationTime": time,
            "requestTime": time,
            "services": rounded_services,
            "totalAmount": f"{total_dec:.2f}",
            "client": {
                "contactPhone": None,
                "displayName": None,
                "inn": None,
                "incomeType": "FROM_INDIVIDUAL",
            },
            "paymentType": "CASH",
            "ignoreMaxTotalIncomeRestriction": False,
        }

        response = cls.req_post("income", json=payload)
        if not response.ok:
            raise RuntimeError(
                f"Invalid response from post_income: {response.status_code} {response.text}"
            )

        uuid = response.json().get("approvedReceiptUuid")
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

        response = cls.req_post("cancel", json=payload)

        if not response.ok:
            raise RuntimeError(
                f"Invalid response from post_cancel: {response.status_code} {response.text}"
            )

        return True

    @classmethod
    def get_check_png(cls, uuid: str) -> bytes:
        response = cls.req_get(f"receipt/{Config.tax_inn()}/{uuid}/print")

        if not response.ok:
            raise RuntimeError(
                f"Invalid response from get_check_png: {response.status_code} {response.text}"
            )

        return response.content
