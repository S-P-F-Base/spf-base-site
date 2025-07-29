from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from data_bases import PaymentDB, ServiceStatus
from templates import templates

router = APIRouter()


@router.get("/pay", response_class=HTMLResponse)
def pay_page(request: Request, uuid: str | None = None):
    if uuid is None:
        raise HTTPException(status_code=400, detail="UUID is required")

    payment_link_data = PaymentDB.payments_links.get_by_u_id(uuid)
    if payment_link_data is None:
        raise HTTPException(status_code=404, detail="Payment link not found")

    payment_uuid = payment_link_data.get("payment_uuid", None)
    if payment_uuid is None:
        raise HTTPException(
            status_code=500, detail="Link has no associated payment UUID"
        )

    payment_data = PaymentDB.payments.get_by_u_id(payment_uuid)
    if payment_data is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    service_data = PaymentDB.services.get_by_u_id(payment_data.what_buy)
    if service_data is None:
        raise HTTPException(status_code=404, detail="Service not found")

    service_meta = service_data.get("meta", None)
    if service_meta is None or isinstance(service_meta, (str, ServiceStatus)):
        raise HTTPException(status_code=500, detail="Service meta is invalid")

    services_name = service_meta.name
    services_value = service_meta.price
    services_description = service_meta.description

    return templates.TemplateResponse(
        "pay.html",
        {
            "request": request,
            "uuid": uuid,
            "services_name": services_name,
            "services_value": str(services_value),
            "services_description": services_description,
        },
    )


@router.post("/pay/confirm")
async def confirm_payment(payment_link: str = Form(...)):
    print(f"Запрос оплаты от пользователя {payment_link}")

    return RedirectResponse(url="/", status_code=303)
