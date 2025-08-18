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


def _is_active(svc: Service) -> bool:
    if svc.status != "on":
        return False

    if svc.left is not None and svc.left <= 0:
        return False

    return True


def _is_inactive(svc: Service) -> bool:
    if svc.status == "off":
        return True

    if svc.status == "on" and svc.left is not None and svc.left <= 0:
        return True

    return False


def _is_archived(svc: Service) -> bool:
    return svc.status == "archive"


@router.get("/donate")
def donate(request: Request):
    rows = PaymentServiceDB.list_services() or []

    active_list: list[dict] = []
    inactive_list: list[dict] = []
    archived_list: list[dict] = []

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
            "discount_time_end": svc.discount_date.replace(microsecond=0).isoformat()
            if discount_active and svc.discount_date
            else "",
            "left": svc.left,
            "status": svc.status,
            "oferta_limit": bool(svc.oferta_limit),
        }

        if _is_archived(svc):
            archived_list.append(item)

        elif _is_active(svc):
            active_list.append(item)

        elif _is_inactive(svc):
            inactive_list.append(item)

        else:
            inactive_list.append(item)

    active_list.sort(key=lambda x: x["name"])
    inactive_list.sort(key=lambda x: x["name"])
    archived_list.sort(key=lambda x: x["name"])

    return templates.TemplateResponse(
        "donate.html",
        {
            "request": request,
            "active_list": active_list,
            "inactive_list": inactive_list,
            "archived_list": archived_list,
        },
    )
