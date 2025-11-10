import hashlib
import hmac
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, cast, get_args

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


def _resolve_commission_key(raw_key: str | None) -> Literal["PC", "AC"]:
    if raw_key and raw_key in get_args(Config.CommissionKey):
        return cast(Config.CommissionKey, raw_key)

    return "AC"


def _expectations_both_scenarios(payment, rate: Decimal) -> dict:
    exp_amt_user, exp_wd_user = payment.expected_amounts(True, rate)
    exp_amt_seller, exp_wd_seller = payment.expected_amounts(False, rate)
    return {
        "seller_pays": {"amount": exp_amt_seller, "withdraw": exp_wd_seller},
        "user_pays": {"amount": exp_amt_user, "withdraw": exp_wd_user},
    }


def _match_scenario(
    amount_dec: Decimal, withdraw_dec: Decimal | None, expectations: dict
) -> tuple[bool, str | None]:
    for scenario, exp in expectations.items():
        exp_amount = exp["amount"]
        exp_withdraw = exp["withdraw"]

        amount_ok = abs(amount_dec - exp_amount) <= EPS
        withdraw_ok = (
            True if withdraw_dec is None else abs(withdraw_dec - exp_withdraw) <= EPS
        )

        if amount_ok and withdraw_ok:
            return True, scenario

    return False, None


def _ensure_tax_receipt(payment_id: str, payment) -> None:
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

    if payment.status == "done":
        _ensure_tax_receipt(payment_id, payment)
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    if payment.status in ("declined", "cancelled"):
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    if (unaccepted or "").lower() == "true" or (codepro or "").lower() == "true":
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    commission_key = _resolve_commission_key(getattr(payment, "commission_key", "AC"))
    rate = dec_rate_from_float(Config.get_commission_rates(commission_key))
    expectations = _expectations_both_scenarios(payment, rate)

    matched, scenario = _match_scenario(amount_dec, withdraw_dec, expectations)

    if not matched:
        logger.warning(
            "Payment %s mismatch: got amount=%s withdraw=%s; "
            "exp(seller)=%s/%s; exp(user)=%s/%s",
            payment_id,
            amount_dec,
            withdraw_dec,
            expectations["seller_pays"]["amount"],
            expectations["seller_pays"]["withdraw"],
            expectations["user_pays"]["amount"],
            expectations["user_pays"]["withdraw"],
        )
        payment.status = "pending"
        PaymentServiceDB.upsert_payment(payment_id, payment)
        return PlainTextResponse("OK", status_code=200)

    payment.status = "done"
    logger.info("Payment %s matched scenario: %s", payment_id, scenario)

    _ensure_tax_receipt(payment_id, payment)
    PaymentServiceDB.upsert_payment(payment_id, payment)

    return PlainTextResponse("OK", status_code=200)


def revalidate(payment_id: str, apply: bool) -> dict:
    payment = PaymentServiceDB.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    commission_key = _resolve_commission_key(getattr(payment, "commission_key", "AC"))
    rate = dec_rate_from_float(Config.get_commission_rates(commission_key))
    expectations = _expectations_both_scenarios(payment, rate)

    amt = payment.received_amount
    wd = payment.payer_amount

    if amt is None:
        return {
            "payment_id": payment_id,
            "status_before": payment.status,
            "matched": False,
            "reason": "No received_amount yet — nothing to validate.",
            "expected": expectations,
        }

    matched, scenario = _match_scenario(amt, wd, expectations)

    result = {
        "payment_id": payment_id,
        "status_before": payment.status,
        "matched": matched,
        "scenario": scenario,
        "received_amount": str(amt) if amt is not None else None,
        "payer_amount": str(wd) if wd is not None else None,
        "expected": {
            "seller_pays": {
                "amount": str(expectations["seller_pays"]["amount"]),
                "withdraw": str(expectations["seller_pays"]["withdraw"]),
            },
            "user_pays": {
                "amount": str(expectations["user_pays"]["amount"]),
                "withdraw": str(expectations["user_pays"]["withdraw"]),
            },
        },
        "total": str(payment.total()),
        "rate": str(rate),
        "eps": str(EPS),
    }

    if matched and apply:
        payment.status = "done"
        _ensure_tax_receipt(payment_id, payment)
        PaymentServiceDB.upsert_payment(payment_id, payment)
        result["status_after"] = payment.status
        result["applied"] = True
    else:
        result["status_after"] = payment.status
        result["applied"] = False

    return result
