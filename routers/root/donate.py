from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Request

from data_bases import PaymentServiceDB, Service
from templates import templates

router = APIRouter()


def _is_discount_active(svc: Service) -> bool:
    if svc.discount_value <= 0:
        return False

    if not svc.discount_date:
        return False

    return svc.discount_date > datetime.now(UTC)


def _is_sold_out(svc: Service) -> bool:
    if svc.status != "on":
        return True

    if svc.left is not None and svc.left <= 0:
        return True

    return False


@router.get("/donate")
def donate(request: Request):
    rows = PaymentServiceDB.list_services()
    if rows is None:
        rows = []

    active_list = []
    no_stock_list = []

    for u_id, svc in rows:
        final_price: Decimal = svc.price()
        discount_active = _is_discount_active(svc)

        item = {
            "u_id": u_id,
            "name": svc.name,
            "description": svc.description,
            "price_main": f"{svc.price_main:.2f}",
            "final_price": f"{final_price:.2f}",
            "discount_value": svc.discount_value if discount_active else 0,
            "discount_time_end": svc.discount_date.isoformat()  # type: ignore
            if discount_active
            else "",
            "left": svc.left,
            "status": svc.status,
            "oferta_limit": bool(svc.oferta_limit),
        }

        if _is_sold_out(svc):
            no_stock_list.append(item)
        else:
            active_list.append(item)

    return templates.TemplateResponse(
        "donate.html",
        {
            "request": request,
            "active_list": active_list,
            "no_stock_list": no_stock_list,
        },
    )
