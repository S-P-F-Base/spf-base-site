import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Final, Literal

from requests import Response, Session

from data_bases.log_db import LogDB, LogType
from data_bases.payment_db import PaymentServiceDB

from .config import Config

TWOPLACES = Decimal("0.01")

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
QUEUE_FILE = DATA_DIR / "tax_income_queue.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return (
        dt.replace(microsecond=0, tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _q2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, ROUND_HALF_UP)


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
    def _request_with_retry(cls, method: str, path: str, **kwargs) -> Response:
        if cls._is_token_expired():
            logging.info("AutoTax: token expired → refresh()")
            cls._refresh()

        url = cls._base_url(path)
        resp = cls._tax_session.request(method, url, **kwargs)
        if resp.status_code == 401:
            logging.warning("AutoTax: got 401 → re-login and retry once")
            cls._login()
            resp = cls._tax_session.request(method, url, **kwargs)

        if not resp.ok:
            raise RuntimeError(
                f"{method.upper()} {path} failed: {resp.status_code} {resp.text}"
            )

        return resp

    @classmethod
    def req_get(cls, path: str, **kwargs) -> Response:
        return cls._request_with_retry("get", path, **kwargs)

    @classmethod
    def req_post(cls, path: str, json=None, **kwargs) -> Response:
        return cls._request_with_retry("post", path, json=json, **kwargs)

    @classmethod
    def _is_token_expired(cls) -> bool:
        if not cls._token_expire:
            return True

        try:
            dt = datetime.fromisoformat(cls._token_expire.replace("Z", "+00:00"))
            return _now_utc() >= dt

        except Exception as e:
            logging.warning(
                f"AutoTax: invalid tokenExpireIn format: {cls._token_expire} ({e})"
            )
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
                "Authorization": f"Bearer {data_json.get('token', '')}",
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
            logging.error(f"AutoTax: login error {resp.status_code}: {resp.text}")
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
            logging.error(f"AutoTax: refresh error {resp.status_code}: {resp.text}")
            return
        cls._update_data(resp.json())

    @classmethod
    def setup(cls) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not QUEUE_FILE.exists():
            QUEUE_FILE.write_text("[]", encoding="utf-8")

        cls._login()

    @classmethod
    def post_income(cls, services: list[tuple[str, Decimal]]) -> str:
        if not services:
            raise ValueError("Services list is empty")

        time = cls._get_cur_time()
        items_dec = [
            {
                "name": name,
                "amount_dec": _q2(Decimal(amount)),
                "quantity": 1,
            }
            for name, amount in services
        ]
        if any(i["amount_dec"] <= 0 for i in items_dec):
            raise ValueError("All service amounts must be > 0")

        total_dec = _q2(sum((i["amount_dec"] for i in items_dec), Decimal("0.00")))
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
        resp = cls.req_post("income", json=payload)
        uuid = resp.json().get("approvedReceiptUuid")
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
        cls.req_post("cancel", json=payload)
        return True

    @classmethod
    def get_check_png(cls, uuid: str) -> bytes:
        resp = cls.req_get(f"receipt/{Config.tax_inn()}/{uuid}/print")
        return resp.content

    # backoff: 1м, 5м
    _BACKOFF = [60, 300]

    @classmethod
    def enqueue_income(
        cls, payment_id: str, services: list[tuple[str, Decimal]]
    ) -> None:
        try:
            queue = cls._load_queue()
            existing = next(
                (x for x in queue if x.get("payment_id") == payment_id), None
            )
            ser = [[name, f"{_q2(Decimal(amount)):.2f}"] for name, amount in services]
            now = _now_utc()
            if existing:
                existing["services"] = ser
                existing.setdefault("attempts", 0)
                existing.setdefault("last_error", None)

            else:
                queue.append(
                    {
                        "payment_id": payment_id,
                        "services": ser,
                        "attempts": 0,
                        "last_error": None,
                        "next_try_ts": _iso(now),
                    }
                )

            cls._save_queue(queue)

        except Exception as e:
            logging.error(f"AutoTax.enqueue_income error: {e}")

    @classmethod
    def _load_queue(cls) -> list[dict]:
        try:
            QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not QUEUE_FILE.exists():
                return []

            return json.loads(QUEUE_FILE.read_text(encoding="utf-8") or "[]")

        except Exception as e:
            logging.error(f"AutoTax._load_queue error: {e}")
            return []

    @classmethod
    def _save_queue(cls, queue: list[dict]) -> None:
        try:
            tmp = QUEUE_FILE.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(QUEUE_FILE)

        except Exception as e:
            logging.error(f"AutoTax._save_queue error: {e}")

    @classmethod
    async def run_queue_worker(
        cls, interval_sec: int = 60, batch_size: int = 10
    ) -> None:
        logging.info("AutoTax queue worker started")
        while True:
            try:
                queue = cls._load_queue()
                now = _now_utc()
                due = []
                rest = []
                for item in queue:
                    ts = item.get("next_try_ts")
                    try_time = (
                        datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else now
                    )
                    (due if try_time <= now else rest).append(item)

                to_process = due[:batch_size]
                processed_ids: set[str] = set()

                for item in to_process:
                    payment_id = item.get("payment_id")
                    services = [
                        (name, Decimal(amount_str))
                        for name, amount_str in item.get("services", [])
                    ]
                    attempts = int(item.get("attempts", 0))

                    try:
                        tax_uuid = cls.post_income(services)
                        pay = PaymentServiceDB.get_payment(payment_id)
                        if pay:
                            pay.tax_check_id = tax_uuid
                            PaymentServiceDB.upsert_payment(payment_id, pay)

                        LogDB.add_log(
                            LogType.PAYMENT_RESIVE,
                            f"[TAX_OK] payment_id={payment_id} tax_id={tax_uuid}",
                            "AutoTax worker",
                        )
                        processed_ids.add(payment_id)

                    except Exception as e:
                        attempts += 1
                        delay = cls._BACKOFF[min(attempts - 1, len(cls._BACKOFF) - 1)]
                        next_ts = _iso(now + timedelta(seconds=delay))
                        item["attempts"] = attempts
                        item["last_error"] = str(e)[:500]
                        item["next_try_ts"] = next_ts
                        rest.append(item)
                        LogDB.add_log(
                            LogType.PAYMENT_RESIVE,
                            f"[TAX_RETRY] payment_id={payment_id} attempts={attempts} next={next_ts} err={e}",
                            "AutoTax worker",
                        )

                remaining = [
                    i for i in rest if i.get("payment_id") not in processed_ids
                ]
                cls._save_queue(remaining)

            except Exception as e:
                logging.error(f"AutoTax worker loop error: {e}")

            await asyncio.sleep(interval_sec)
