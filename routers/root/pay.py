from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import PaymentStatus, YoomoneyDB

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/pay/{uuid}")
def pay(uuid: str):
    payment_id = YoomoneyDB.resolve_payment_id_by_uuid(uuid)
    if payment_id is None:
        raise HTTPException(status_code=404, detail="Payment link not found")

    payment = YoomoneyDB.get_payment_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] == PaymentStatus.done:
        return RedirectResponse(f"/pay/{uuid}/success")
    elif payment["status"] == PaymentStatus.cancel:
        return RedirectResponse(f"/pay/{uuid}/cancel")
    else:
        amount = YoomoneyDB.price_calculation(
            amount=payment["amount"] - payment["receive"],
            payment_type="AC",
        )

        url = YoomoneyDB.generate_yoomoney_payment_url(
            amount=amount,
            successURL=f"https://spf-base.ru/pay/{uuid}/success",
            label=payment["id"],
            payment_type="AC",
        )
        return RedirectResponse(url)


@router.get("/pay/{uuid}/success", response_class=HTMLResponse)
def pay_success(request: Request, uuid: str):
    if uuid == "test":
        return templates.TemplateResponse(
            "pay_success.html",
            {"request": request, "uuid": uuid},
        )

    payment_id = YoomoneyDB.resolve_payment_id_by_uuid(uuid)
    if payment_id is None:
        raise HTTPException(status_code=404, detail="Payment link not found")

    payment = YoomoneyDB.get_payment_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] != PaymentStatus.done:
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

    payment_id = YoomoneyDB.resolve_payment_id_by_uuid(uuid)
    if payment_id is None:
        raise HTTPException(status_code=404, detail="Payment link not found")

    payment = YoomoneyDB.get_payment_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] != PaymentStatus.cancel:
        return RedirectResponse(f"/pay/{uuid}")

    return templates.TemplateResponse(
        "pay_cancel.html",
        {"request": request, "uuid": uuid},
    )
