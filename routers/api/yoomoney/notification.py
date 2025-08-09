import hashlib
import hmac
from decimal import ROUND_HALF_UP, Decimal
from typing import cast, get_args

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import PlainTextResponse

from data_bases import LogDB, LogType, PaymentServiceDB
from data_control import AutoTax, Config

router = APIRouter()

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
        raise HTTPException(status_code=400, detail="Empty label")

    payment_id = label
    payment = PaymentServiceDB.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        amount_dec = q2(Decimal(amount))
        withdraw_dec = q2(Decimal(withdraw_amount)) if withdraw_amount else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount format")

    payment.received_amount = amount_dec
    payment.payer_amount = withdraw_dec

    if payment.status in ("declined", "cancelled"):
        LogDB.add_log(
            LogType.PAYMENT_RESIVE,
            (
                f"[IGNORED_{payment.status.upper()}] payment_id={payment_id} "
                f"op_id={operation_id} amount={amount_dec} withdraw={withdraw_dec} currency={currency}"
            ),
            "YooMoney notification",
        )
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    raw_key = getattr(payment, "commission_key", "AC")
    if raw_key in get_args(Config.CommissionKey):
        commission_key: Config.CommissionKey = cast(Config.CommissionKey, raw_key)
    else:
        commission_key = "AC"

    rate = dec_rate_from_float(Config.get_commission_rates(commission_key))
    user_pays = Config.user_pays_commission()

    expected_amount, expected_withdraw = payment.expected_amounts(user_pays, rate)

    amount_ok = abs(amount_dec - expected_amount) <= EPS
    withdraw_ok = True
    if withdraw_dec is not None:
        withdraw_ok = abs(withdraw_dec - expected_withdraw) <= EPS

    if not (amount_ok and withdraw_ok):
        overpay = amount_dec > expected_amount + EPS
        underpay = amount_dec < expected_amount - EPS

        LogDB.add_log(
            LogType.PAYMENT_RESIVE,
            (
                f"[AMOUNT_MISMATCH] payment_id={payment_id} op_id={operation_id} "
                f"total={payment.total()} key={commission_key} rate={rate}; "
                f"expected_amount={expected_amount}, got={amount_dec}; "
                f"expected_withdraw={expected_withdraw}, got={withdraw_dec}; "
                f"overpay={overpay} underpay={underpay} currency={currency}"
            ),
            "YooMoney notification",
        )
        payment.status = "pending"
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    try:
        if not getattr(payment, "tax_check_id", None) and payment.status != "done":
            tax_uuid = AutoTax.post_income(payment.to_fns_struct())
            payment.tax_check_id = tax_uuid

        payment.status = "done"

    except Exception as e:
        LogDB.add_log(
            LogType.PAYMENT_RESIVE,
            f"Failed to send tax receipt for {payment_id}: {e}",
            "YooMoney notification",
        )
        payment.status = "pending"

    PaymentServiceDB.upsert_payment(payment_id, payment)

    LogDB.add_log(
        LogType.PAYMENT_RESIVE,
        f"Confirmation of payment: {payment_id}, status={payment.status}, op_id={operation_id}",
        "YooMoney notification",
    )

    return PlainTextResponse("OK", status_code=200)
