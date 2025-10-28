import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

import utils.admin
import utils.error
from data_bases import PaymentServiceDB
from data_bases import Service as ServiceModel
from templates import templates

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/profile/admin/services")
async def admin_services(request: Request):
    utils.admin.require_access(request, "edit_services")
    rows = PaymentServiceDB.list_services()
    items = []
    for u, svc in rows:
        d = svc.to_dict()
        items.append(
            {
                "u_id": u,
                "name": d.get("name"),
                "description": d.get("description"),
                "status": d.get("status"),
                "price_main": d.get("price_main"),
                "discount_value": d.get("discount_value"),
                "discount_date": d.get("discount_date"),
                "left": d.get("left"),
                "sell_time": d.get("sell_time"),
                "oferta_limit": d.get("oferta_limit"),
                "creation_date": d.get("creation_date"),
                "final_price": f"{svc.price():.2f}",
            }
        )
    return templates.TemplateResponse(
        "profile/admin/services.html",
        {"request": request, "authenticated": True, "services": items},
    )


@router.post("/profile/admin/service/create")
async def service_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price_main: str = Form(...),
    discount_value: int = Form(0),
    discount_date_raw: str | None = Form(None),
    status: str = Form("off"),
    left_raw: str | None = Form(None),
    sell_time: str | None = Form(None),
    oferta_limit: bool = Form(False),
):
    utils.admin.require_access(request, "edit_services")

    left = (
        int(left_raw)
        if left_raw
        not in (
            None,
            "",
        )
        else None
    )
    discount_date = discount_date_raw or None

    payload = {
        "name": name,
        "description": description,
        "creation_date": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "price_main": price_main,
        "discount_value": discount_value,
        "discount_date": discount_date,
        "status": status,
        "left": left,
        "sell_time": sell_time,
        "oferta_limit": bool(oferta_limit),
    }
    svc = ServiceModel.from_dict(payload)
    PaymentServiceDB.upsert_service(uuid.uuid4().hex, svc)
    return RedirectResponse("/profile/admin/services", status_code=303)


@router.post("/profile/admin/service/update")
async def service_update(
    request: Request,
    u_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    price_main: str = Form(...),
    discount_value: int = Form(0),
    discount_date_raw: str | None = Form(None),
    status: str = Form("off"),
    left_raw: str | None = Form(None),
    sell_time: str | None = Form(None),
    oferta_limit: bool = Form(False),
):
    utils.admin.require_access(request, "edit_services")

    current = PaymentServiceDB.get_service(u_id)
    if not current:
        utils.error.not_found("service_not_found", "Service not found", u_id=u_id)
        return

    left = (
        int(left_raw)
        if left_raw
        not in (
            None,
            "",
        )
        else None
    )
    discount_date = discount_date_raw or None

    patch = {
        "name": name,
        "description": description,
        "price_main": price_main,
        "discount_value": discount_value,
        "discount_date": discount_date,
        "status": status,
        "left": left,
        "sell_time": sell_time,
        "oferta_limit": bool(oferta_limit),
    }

    merged = current.to_dict()  # type: ignore
    merged.update(patch)
    updated = ServiceModel.from_dict(merged)
    PaymentServiceDB.upsert_service(u_id, updated)

    return RedirectResponse("/profile/admin/services", status_code=303)


@router.post("/profile/admin/service/delete")
async def service_delete(request: Request, u_id: str = Form(...)):
    utils.admin.require_access(request, "edit_services")
    PaymentServiceDB.delete_service(u_id)
    return RedirectResponse("/profile/admin/services", status_code=303)
