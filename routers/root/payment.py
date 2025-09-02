from decimal import Decimal
from typing import Literal
from urllib.parse import quote, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from data_bases import PaymentServiceDB
from data_control import AutoTax, Config
from templates import templates

router = APIRouter()


def _price_calculation(
    amount: Decimal,
    payment_type: Literal["PC", "AC"] = "AC",
) -> Decimal:
    sum_to_pay = amount

    if Config.user_pays_commission():
        commission = Decimal(str(Config.get_commission_rates(payment_type)))
        if payment_type == "PC":
            sum_to_pay = amount / (
                Decimal("1") - commission / (Decimal("1") + commission)
            )
        elif payment_type == "AC":
            sum_to_pay = amount / (Decimal("1") - commission)
        else:
            raise ValueError("Unknown type of payment_type")

    return sum_to_pay.quantize(Decimal("0.01"))


def _generate_yoomoney_payment_url(
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


@router.get("/payment/{payment_uuid}", response_class=HTMLResponse)
def pay_page(request: Request, payment_uuid: str):
    payment = PaymentServiceDB.get_payment(str(payment_uuid))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")

    if payment.status != "pending":
        return RedirectResponse(url=f"/payment/{payment_uuid}/status", status_code=303)

    return templates.TemplateResponse(
        "payment/pay.html",
        {
            "request": request,
            "payment": payment,
            "payment_uuid": str(payment_uuid),
            "user_pays_commission": Config.user_pays_commission(),
        },
    )


@router.get("/payment/{payment_uuid}/status", response_class=HTMLResponse)
def payment_status(request: Request, payment_uuid: str):
    payment = PaymentServiceDB.get_payment(str(payment_uuid))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")

    return templates.TemplateResponse(
        "payment/status.html",
        {
            "request": request,
            "payment": payment,
            "payment_uuid": str(payment_uuid),
            "user_pays_commission": Config.user_pays_commission(),
        },
    )


@router.get("/payment/{payment_uuid}/submit")
def payment_submit(request: Request, payment_uuid: str):
    payment = PaymentServiceDB.get_payment(str(payment_uuid))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")

    if payment.status != "pending":
        raise HTTPException(status_code=409, detail=f"payment is {payment.status}")

    base_total = payment.total()
    payment_type: Literal["PC", "AC"] = payment.commission_key  # type: ignore

    sum_to_pay = _price_calculation(base_total, payment_type)

    success_url = f"https://spf-base.ru/payment/{payment_uuid}/status"

    label = payment_uuid

    redirect_url = _generate_yoomoney_payment_url(
        amount=sum_to_pay,
        successURL=success_url,
        label=label,
        payment_type=payment_type,
    )
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/payment/{payment_uuid}/receipt.png")
def download_receipt_png(request: Request, payment_uuid: str):
    payment = PaymentServiceDB.get_payment(str(payment_uuid))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")

    if payment.status != "done":
        raise HTTPException(status_code=409, detail=f"payment is {payment.status}")

    tax_uuid = getattr(payment, "tax_check_id", None)
    if not tax_uuid:
        raise HTTPException(status_code=404, detail="tax check id is missing")

    try:
        content = AutoTax.get_check_png(tax_uuid)
        if not isinstance(content, (bytes, bytearray)):
            raise RuntimeError("receipt content is not bytes")

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"failed to fetch receipt: {e}")

    filename_utf8 = f"чек {tax_uuid}.png"
    filename_ascii = f"check-{tax_uuid}.png"

    disp = f"attachment; filename={filename_ascii}; filename*=UTF-8''{quote(filename_utf8)}"

    headers = {
        "Content-Disposition": disp,
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content, media_type="image/png", headers=headers)
