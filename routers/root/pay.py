from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from data_bases import YoomoneyDB
from data_control import PaymentData
from templates import templates

router = APIRouter()


def _get_payment_by_uuid(uuid: str) -> PaymentData:
    payment_id = YoomoneyDB.resolve_payment_id_by_uuid(uuid)
    if payment_id is None:
        raise HTTPException(status_code=404, detail="Payment link not found")

    payment = YoomoneyDB.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@router.get("/pay/{uuid}", response_class=HTMLResponse)
def pay_get(
    request: Request,
    uuid: str,
    confirm: bool = False,
):
    if uuid == "test":
        return templates.TemplateResponse(
            "pay_confirm.html",
            {
                "request": request,
                "uuid": uuid,
                "amount": 199.99,
                "test": True,
                "reason": "Тестовая услуга",
            },
        )

    payment = _get_payment_by_uuid(uuid)

    if payment.is_complete():
        return RedirectResponse(f"/pay/{uuid}/success")
    elif payment.is_cancel():
        return RedirectResponse(f"/pay/{uuid}/cancel")

    if payment.db_id is None:
        raise HTTPException(status_code=500, detail="Empty id of payment")

    if confirm:
        url = YoomoneyDB.generate_yoomoney_payment_url(
            amount=payment.price_calculation_by_payment("AC"),
            successURL=f"https://spf-base.ru/pay/{uuid}/success",
            label=str(payment.db_id),
            payment_type="AC",
        )
        return RedirectResponse(url)

    return templates.TemplateResponse(
        "pay_confirm.html",
        {
            "request": request,
            "uuid": uuid,
            "amount": payment.amount,
            "reason": payment.what_buy,  # TODO: Сделать ресолв из id в строку
        },
    )


@router.get("/pay/{uuid}/success", response_class=HTMLResponse)
def pay_success(request: Request, uuid: str):
    if uuid == "test":
        return templates.TemplateResponse(
            "pay_success.html",
            {"request": request, "uuid": uuid},
        )

    payment = _get_payment_by_uuid(uuid)

    if not payment.is_complete():
        return RedirectResponse(f"/pay/{uuid}")

    return templates.TemplateResponse(
        "pay_success.html",
        {"request": request, "uuid": uuid},
    )


@router.get("/pay/{uuid}/cancel", response_class=HTMLResponse)
def pay_cancel(request: Request, uuid: str):
    if uuid == "test":
        return templates.TemplateResponse(
            "pay_cancel.html",
            {"request": request, "uuid": uuid},
        )

    payment = _get_payment_by_uuid(uuid)

    if not payment.is_cancel():
        return RedirectResponse(f"/pay/{uuid}")

    return templates.TemplateResponse(
        "pay_cancel.html",
        {"request": request, "uuid": uuid},
    )
