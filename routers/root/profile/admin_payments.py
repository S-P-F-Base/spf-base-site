import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

import utils.admin
import utils.error
from data_bases import (
    Payment as PaymentModel,
)
from data_bases import (
    PaymentServiceDB,
    ServiceSnapshot,
)
from data_bases import (
    Service as ServiceModel,
)
from templates import templates

logger = logging.getLogger(__name__)
router = APIRouter()

PaymentStatus = Literal["pending", "declined", "cancelled", "done"]
CommissionKey = Literal["PC", "AC"]


def _build_snapshots(items: list[dict]) -> list[ServiceSnapshot]:
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    want: dict[str, int] = {}
    for entry in items:
        svc_id = (entry.get("service_u_id") or "").strip()
        if not svc_id:
            raise ValueError("service_u_id is required for each item")

        try:
            qty = int(entry.get("qty", 1))
        except Exception:
            raise ValueError(f"qty must be int for {svc_id}")

        if qty <= 0:
            raise ValueError(f"qty must be >= 1 for {svc_id}")

        want[svc_id] = want.get(svc_id, 0) + qty

    cache: dict[str, ServiceModel] = {}
    for svc_id, qty in want.items():
        svc = PaymentServiceDB.get_service(svc_id)
        if not svc:
            raise ValueError(f"Service not found: {svc_id}")
        if svc.status != "on":
            raise ValueError(f"Service is not active: {svc_id}")
        if svc.left is not None and svc.left < qty:
            raise ValueError(
                f"Not enough stock for {svc_id}: need {qty}, left {svc.left}"
            )
        cache[svc_id] = svc

    decremented: list[tuple[str, int]] = []
    try:
        for svc_id, qty in want.items():
            if not PaymentServiceDB.decrement_service_left(svc_id, qty):
                raise ValueError(f"Failed to decrement stock for {svc_id}")
            decremented.append((svc_id, qty))
    except Exception:
        for svc_id, qty in reversed(decremented):
            PaymentServiceDB.increment_service_left(svc_id, qty)
        raise

    snaps: list[ServiceSnapshot] = []
    for svc_id, qty in want.items():
        svc = cache[svc_id]
        for _ in range(qty):
            snaps.append(
                ServiceSnapshot(
                    name=svc.name,
                    creation_date=svc.creation_date,
                    price_main=svc.price_main,
                    discount_value=svc.discount_value,
                    service_u_id=svc_id,
                )
            )

    return snaps


@router.get("/profile/admin/payments")
async def admin_payments(request: Request):
    utils.admin.require_admin(request)

    rows = PaymentServiceDB.list_payments()
    payments = []
    for u_id, pay in rows:
        payments.append(
            {
                "u_id": u_id,
                "status": pay.status,
                "player_id": pay.player_id,
                "commission_key": pay.commission_key,
                "snapshot_len": len(pay.snapshot),
                "snapshot": [s.to_dict() for s in pay.snapshot],
                "total": f"{pay.total():.2f}",
                "tax_check_id": pay.tax_check_id,
                "received_amount": (
                    f"{pay.received_amount:.2f}"
                    if pay.received_amount is not None
                    else None
                ),
                "payer_amount": (
                    f"{pay.payer_amount:.2f}" if pay.payer_amount is not None else None
                ),
            }
        )

    svc_rows = PaymentServiceDB.list_services()
    services = []
    for u, svc in svc_rows:
        if svc.status != "on":
            continue
        d = svc.to_dict()
        services.append(
            {
                "u_id": u,
                "name": d.get("name"),
                "final_price": f"{svc.price():.2f}",
                "left": d.get("left"),
            }
        )

    return templates.TemplateResponse(
        "profile/admin/payments.html",
        {
            "request": request,
            "authenticated": True,
            "payments": payments,
            "services": services,
        },
    )


@router.post("/profile/admin/payment/create")
async def payment_create(
    request: Request,
    player_id: str = Form(...),
    commission_key: CommissionKey = Form("AC"),
    status: PaymentStatus = Form("pending"),
    service_u_id: list[str] = Form(...),
    qty: list[int] = Form(...),
):
    utils.admin.require_access(request, "edit_payments")

    if len(service_u_id) != len(qty):
        utils.error.bad_request("invalid_items", "Mismatched items arrays")

    items = []
    for s, q in zip(service_u_id, qty):
        raw = (s or "").strip()
        clean = raw.replace("`", "")
        if clean.startswith("service_"):
            clean = clean[len("service_") :]

        items.append({"service_u_id": clean, "qty": int(q)})

    try:
        snapshots = _build_snapshots(items)
    except ValueError as e:
        utils.error.bad_request("build_snapshots_failed", str(e))

    pay = PaymentModel(
        status=status,
        player_id=player_id,
        snapshot=snapshots,  # type: ignore
        commission_key=commission_key,
        tax_check_id=None,
        received_amount=None,
        payer_amount=None,
    )
    u_id = uuid.uuid4().hex
    PaymentServiceDB.upsert_payment(u_id, pay)

    return RedirectResponse("/profile/admin/payments", status_code=303)


@router.post("/profile/admin/payment/update")
async def payment_update(
    request: Request,
    u_id: str = Form(...),
    status: PaymentStatus | None = Form(None),
    player_id: str | None = Form(None),
    commission_key: CommissionKey | None = Form(None),
):
    utils.admin.require_access(request, "edit_payments")

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        utils.error.not_found("payment_not_found", "Payment not found", u_id=u_id)
        return

    if status is not None and pay.status == "done" and status != "cancelled":
        utils.error.bad_request(
            "status_locked", "Cannot change status of a completed payment"
        )
        return

    old_status = pay.status

    if status is not None and status != pay.status:
        if old_status == "pending" and status in ("cancelled", "declined"):
            restored = 0
            for snap in pay.snapshot:
                svc_id = getattr(snap, "service_u_id", None)
                if svc_id:
                    PaymentServiceDB.increment_service_left(svc_id, 1)
                    restored += 1
            logger.info("Restored %d items for %s", restored, u_id)
        pay.status = status

    if player_id is not None and player_id != pay.player_id:
        pay.player_id = player_id

    if commission_key is not None and commission_key != pay.commission_key:
        pay.commission_key = commission_key

    PaymentServiceDB.upsert_payment(u_id, pay)
    return RedirectResponse("/profile/admin/payments", status_code=303)


@router.post("/profile/admin/payment/delete")
async def payment_delete(request: Request, u_id: str = Form(...)):
    utils.admin.require_access(request, "edit_payments")

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        utils.error.not_found("payment_not_found", "Payment not found", u_id=u_id)
        return

    if pay.status == "pending":
        for snap in pay.snapshot:
            svc_id = getattr(snap, "service_u_id", None)
            if svc_id:
                PaymentServiceDB.increment_service_left(svc_id, 1)

    ok = PaymentServiceDB.delete_payment(u_id)
    if not ok:
        utils.error.server_error(
            "payment_delete_failed", "Failed to delete payment", u_id=u_id
        )

    return RedirectResponse("/profile/admin/payments", status_code=303)
