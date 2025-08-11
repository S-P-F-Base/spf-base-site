import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from .base_db import BaseDB

TWOPLACES = Decimal("0.01")


def _clamp_discount(v: int) -> int:
    return 0 if v < 0 else 100 if v > 100 else v


def _dt_to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.isoformat()


def _dt_from_iso(s: str | None) -> datetime:
    if s is None:
        return datetime.now(UTC)

    return datetime.fromisoformat(s)


def _dec_to_str(d: Decimal) -> str:
    return f"{q2(d)}"


def _dec_from_str(s: str) -> Decimal:
    return Decimal(s)


def _dec_to_str_opt(d: Decimal | None) -> str | None:
    if d is None:
        return None

    return _dec_to_str(d)


def _dec_from_str_opt(s: str | None) -> Decimal | None:
    if s is None or s == "":
        return None

    return _dec_from_str(s)


def q2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, ROUND_HALF_UP)


@dataclass
class Service:
    name: str
    description: str
    creation_date: datetime

    price_main: Decimal

    discount_value: int  # 0-100
    discount_date: datetime | None

    status: Literal["on", "off", "archive"]
    left: int | None
    sell_time: datetime | None

    oferta_limit: bool

    def price(self) -> Decimal:
        now = datetime.now(UTC)
        dv = _clamp_discount(self.discount_value)
        if self.discount_date and self.discount_date > now and 0 < dv < 100:
            multiplier = Decimal(1) - (Decimal(dv) / Decimal(100))
            return q2(self.price_main * multiplier)

        return q2(self.price_main)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "creation_date": _dt_to_iso(self.creation_date),
            "price_main": _dec_to_str(self.price_main),
            "discount_value": int(_clamp_discount(self.discount_value)),
            "discount_date": _dt_to_iso(self.discount_date),
            "status": self.status,
            "left": self.left,
            "sell_time": _dt_to_iso(self.sell_time),
            "oferta_limit": bool(self.oferta_limit),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Service":
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            creation_date=_dt_from_iso(d["creation_date"]),
            price_main=_dec_from_str(d["price_main"]),
            discount_value=int(_clamp_discount(d.get("discount_value", 0))),
            discount_date=_dt_from_iso(d.get("discount_date")),
            status=d.get("status", "off"),
            left=d.get("left"),
            sell_time=_dt_from_iso(d.get("sell_time")),
            oferta_limit=bool(d.get("oferta_limit", False)),
        )


@dataclass
class ServiceSnapshot:
    name: str
    creation_date: datetime
    price_main: Decimal
    discount_value: int  # 0-100

    # link to original service to allow stock restore on cancel
    service_u_id: str | None = None

    def price(self) -> Decimal:
        dv = _clamp_discount(self.discount_value)
        if 0 < dv < 100:
            multiplier = Decimal(1) - (Decimal(dv) / Decimal(100))
            return q2(self.price_main * multiplier)
        return q2(self.price_main)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "creation_date": _dt_to_iso(self.creation_date),
            "price_main": _dec_to_str(self.price_main),
            "discount_value": int(_clamp_discount(self.discount_value)),
            "service_u_id": self.service_u_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ServiceSnapshot":
        return cls(
            name=d["name"],
            creation_date=_dt_from_iso(d["creation_date"]),
            price_main=_dec_from_str(d["price_main"]),
            discount_value=int(_clamp_discount(d.get("discount_value", 0))),
            service_u_id=d.get("service_u_id"),
        )


@dataclass
class Payment:
    status: Literal["pending", "declined", "cancelled", "done"]

    player_id: str

    snapshot: list[ServiceSnapshot]

    commission_key: Literal["PC", "AC"] = "AC"
    tax_check_id: str | None = None

    received_amount: Decimal | None = None
    payer_amount: Decimal | None = None

    def to_fns_struct(self) -> list[tuple[str, Decimal]]:
        return [
            (
                f"{item.name} (от {item.creation_date.strftime('%d.%m.%Y')})",
                item.price(),
            )
            for item in self.snapshot
        ]

    def total(self) -> Decimal:
        return q2(sum((p[1] for p in self.to_fns_struct()), Decimal("0.00")))

    def expected_amounts(
        self,
        user_pays_commission: bool,
        rate: Decimal,
    ) -> tuple[Decimal, Decimal]:
        total = self.total()
        if user_pays_commission:
            expected_amount = total
            expected_withdraw = q2(total * (Decimal(1) + rate))

        else:
            expected_amount = q2(total * (Decimal(1) - rate))
            expected_withdraw = total

        return expected_amount, expected_withdraw

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "player_id": self.player_id,
            "snapshot": [s.to_dict() for s in self.snapshot],
            "commission_key": self.commission_key,
            "tax_check_id": self.tax_check_id,
            "received_amount": _dec_to_str_opt(self.received_amount),
            "payer_amount": _dec_to_str_opt(self.payer_amount),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Payment":
        return cls(
            status=d["status"],
            player_id=d["player_id"],
            snapshot=[ServiceSnapshot.from_dict(x) for x in d.get("snapshot", [])],
            commission_key=d.get("commission_key", "AC"),
            tax_check_id=d.get("tax_check_id"),
            received_amount=_dec_from_str_opt(d.get("received_amount")),
            payer_amount=_dec_from_str_opt(d.get("payer_amount")),
        )


class PaymentServiceDB(BaseDB):
    _db_name = "PaymentService"

    @classmethod
    def create_db_table(cls) -> None:
        super().create_db_table()
        with cls._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS service (
                    u_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS payment (
                    u_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
            """)
            con.commit()

    @classmethod
    def upsert_service(cls, u_id: str, service: Service) -> None:
        payload = json.dumps(service.to_dict(), ensure_ascii=False)
        with cls._connect() as con:
            con.execute(
                """
                INSERT INTO service (u_id, data) VALUES (?, ?)
                ON CONFLICT(u_id) DO UPDATE SET data=excluded.data
            """,
                (u_id, payload),
            )
            con.commit()

    @classmethod
    def get_service(cls, u_id: str) -> Service | None:
        with cls._connect() as con:
            cur = con.execute("SELECT data FROM service WHERE u_id=?", (u_id,))
            row = cur.fetchone()

        if not row:
            return None

        return Service.from_dict(json.loads(row[0]))

    @classmethod
    def list_services(cls) -> list[tuple[str, Service]]:
        with cls._connect() as con:
            cur = con.execute("SELECT u_id, data FROM service")
            rows = cur.fetchall()

        return [(u, Service.from_dict(json.loads(j))) for (u, j) in rows]

    @classmethod
    def delete_service(cls, u_id: str) -> bool:
        with cls._connect() as con:
            cur = con.execute("DELETE FROM service WHERE u_id=?", (u_id,))
            con.commit()
            return cur.rowcount > 0

    @classmethod
    def decrement_service_left(cls, service_u_id: str, qty: int = 1) -> bool:
        if qty <= 0:
            return True
        svc = cls.get_service(service_u_id)
        if not svc:
            return False
        if svc.left is None:
            return True
        if svc.left < qty:
            return False
        svc.left -= qty
        cls.upsert_service(service_u_id, svc)
        return True

    @classmethod
    def increment_service_left(cls, service_u_id: str, qty: int = 1) -> bool:
        if qty <= 0:
            return True
        svc = cls.get_service(service_u_id)
        if not svc:
            return False
        if svc.left is None:
            return True
        svc.left += qty
        cls.upsert_service(service_u_id, svc)
        return True

    @classmethod
    def upsert_payment(cls, u_id: str, payment: Payment) -> None:
        payload = json.dumps(payment.to_dict(), ensure_ascii=False)
        with cls._connect() as con:
            con.execute(
                """
                INSERT INTO payment (u_id, data) VALUES (?, ?)
                ON CONFLICT(u_id) DO UPDATE SET data=excluded.data
            """,
                (u_id, payload),
            )
            con.commit()

    @classmethod
    def get_payment(cls, u_id: str) -> Payment | None:
        with cls._connect() as con:
            cur = con.execute("SELECT data FROM payment WHERE u_id=?", (u_id,))
            row = cur.fetchone()

        if not row:
            return None

        return Payment.from_dict(json.loads(row[0]))

    @classmethod
    def list_payments(cls) -> list[tuple[str, Payment]]:
        with cls._connect() as con:
            cur = con.execute("SELECT u_id, data FROM payment")
            rows = cur.fetchall()

        return [(u, Payment.from_dict(json.loads(j))) for (u, j) in rows]

    @classmethod
    def delete_payment(cls, u_id: str) -> bool:
        with cls._connect() as con:
            cur = con.execute("DELETE FROM payment WHERE u_id=?", (u_id,))
            con.commit()
            return cur.rowcount > 0
