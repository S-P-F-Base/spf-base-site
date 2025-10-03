import hashlib
import hmac
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import cast, get_args

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import PlainTextResponse

from data_bases import PaymentServiceDB
from data_control import AutoTax, Config

router = APIRouter()

logger = logging.getLogger(__name__)

TWOPLACES = Decimal("0.01")
EPS = Decimal("0.01")


def q2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, ROUND_HALF_UP)


def dec_rate_from_float(x: float) -> Decimal:
    return Decimal(str(x))


@router.post("/notification", response_class=PlainTextResponse)
def yoomoney_notification(
    notification_type: str = Form(...),
    operation_id: str = Form(...),
    amount: str = Form(...),
    currency: str = Form(...),
    datetime: str = Form(...),
    sender: str = Form(...),
    codepro: str = Form(...),
    sha1_hash: str = Form(...),
    label: str = Form(""),
    withdraw_amount: str = Form(""),
    unaccepted: str = Form("", alias="unaccepted"),
):
    check_string = "&".join(
        [
            notification_type,
            operation_id,
            amount,
            currency,
            datetime,
            sender,
            codepro,
            Config.yoomoney_notification(),
            label,
        ]
    )
    calc = hashlib.sha1(check_string.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(calc, sha1_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid hash"
        )

    if not label:
        return PlainTextResponse("OK", status_code=200)

    payment_id = label
    payment = PaymentServiceDB.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        amount_dec = q2(Decimal(amount))
        withdraw_dec = q2(Decimal(withdraw_amount)) if withdraw_amount else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount format")

    if payment.received_amount:
        payment.received_amount += amount_dec
    else:
        payment.received_amount = amount_dec

    if withdraw_dec:
        if payment.payer_amount:
            payment.payer_amount += withdraw_dec
        else:
            payment.payer_amount = withdraw_dec

    def ensure_tax_receipt() -> None:
        if getattr(payment, "tax_check_id", None):
            AutoTax.remove_from_queue(payment_id)
            return

        services = payment.to_fns_struct()
        if not services:
            logger.error("Payment %s has no services for tax receipt", payment_id)
            return

        try:
            tax_uuid = AutoTax.post_income(services)
            payment.tax_check_id = tax_uuid
            AutoTax.remove_from_queue(payment_id)

        except Exception as exc:
            logger.error("AutoTax.post_income failed for %s: %s", payment_id, exc)
            AutoTax.enqueue_income(payment_id, services)

    if payment.status == "done":
        ensure_tax_receipt()
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    if payment.status in ("declined", "cancelled"):
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    if (unaccepted or "").lower() == "true" or (codepro or "").lower() == "true":
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    raw_key = getattr(payment, "commission_key", "AC")
    if raw_key in get_args(Config.CommissionKey):
        commission_key = cast(Config.CommissionKey, raw_key)

    else:
        commission_key = "AC"

    rate = dec_rate_from_float(Config.get_commission_rates(commission_key))
    user_pays = Config.user_pays_commission()
    expected_amount, expected_withdraw = payment.expected_amounts(user_pays, rate)

    amount_ok = abs(amount_dec - expected_amount) <= EPS
    withdraw_ok = (
        True if withdraw_dec is None else abs(withdraw_dec - expected_withdraw) <= EPS
    )

    if not (amount_ok and withdraw_ok):
        payment.status = "pending"
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    payment.status = "done"

    ensure_tax_receipt()
    PaymentServiceDB.upsert_payment(payment_id, payment)

    return PlainTextResponse("OK", status_code=200)
