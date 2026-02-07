from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from data_control import Config
from templates import templates

router = APIRouter()

MIN_AMOUNT = Decimal("10.00")
MAX_AMOUNT = Decimal("50000.00")

_ONE = Decimal("1")


def _price_calculation(
    amount: Decimal,
    payment_type: Literal["PC", "AC"] = "AC",
    cover_commission: bool = False,
) -> Decimal:
    sum_to_pay = amount

    if cover_commission:
        commission = Decimal(str(Config.get_commission_rates(payment_type)))
        if commission < 0 or commission >= 1:
            raise HTTPException(
                status_code=500, detail="commission: out of bounds [0,1)"
            )

        if payment_type == "PC":
            denom = _ONE - commission / (_ONE + commission)
            if denom <= 0:
                raise HTTPException(
                    status_code=500, detail="commission: invalid denominator (PC)"
                )
            sum_to_pay = amount / denom
        elif payment_type == "AC":
            denom = _ONE - commission
            if denom <= 0:
                raise HTTPException(
                    status_code=500, detail="commission: invalid denominator (AC)"
                )
            sum_to_pay = amount / denom
        else:
            raise HTTPException(status_code=400, detail="payment_type: unknown")

    return sum_to_pay.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _generate_yoomoney_payment_url(
    amount: Decimal,
    payment_type: Literal["PC", "AC"] = "AC",
) -> str:
    params = {
        "receiver": Config.yoomoney_account(),
        "quickpay-form": "button",
        "paymentType": payment_type,
        "sum": str(amount),
        "label": "",
        "successURL": "https://spf-base.ru/donate/thanks",
    }
    return f"https://yoomoney.ru/quickpay/confirm?{urlencode(params)}"


def _parse_amount(raw: str) -> Decimal:
    s = (raw or "").strip().replace(",", ".")
    if not s:
        raise HTTPException(status_code=400, detail="amount: empty")

    try:
        val = Decimal(s)
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="amount: invalid number")

    if val <= 0:
        raise HTTPException(status_code=400, detail="amount: must be > 0")

    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/donate", response_class=HTMLResponse)
def donate_page(request: Request):
    raise HTTPException(404)
    return templates.TemplateResponse(
        "donate/index.html",
        {
            "request": request,
            "min_amount": str(MIN_AMOUNT),
            "max_amount": str(MAX_AMOUNT),
        },
    )


@router.post("/donate/submit")
def donate_submit(
    request: Request,
    amount: str = Form(...),
    method: Literal["AC", "PC"] = Form(...),
    cover_commission: bool = Form(False),
):
    raise HTTPException(404)
    amt = _parse_amount(amount)

    if amt < MIN_AMOUNT or amt > MAX_AMOUNT:
        return templates.TemplateResponse(
            "donate/index.html",
            {
                "request": request,
                "min_amount": str(MIN_AMOUNT),
                "max_amount": str(MAX_AMOUNT),
                "error": f"Amount must be between {MIN_AMOUNT} and {MAX_AMOUNT}",
                "amount": str(amt),
                "method": method,
                "cover_commission": cover_commission,
            },
            status_code=400,
        )

    amount_to_pay = _price_calculation(amt, method, cover_commission)

    redirect_url = _generate_yoomoney_payment_url(
        amount=amount_to_pay,
        payment_type=method,
    )
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/donate/thanks", response_class=HTMLResponse)
def donate_thanks(request: Request):
    raise HTTPException(404)
    return templates.TemplateResponse(
        "donate/thanks.html",
        {"request": request},
    )
