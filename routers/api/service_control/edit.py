from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_bases import Service as ServiceModel
from data_control import req_authorization

router = APIRouter()
UNSET = object()


@router.post("/edit")
def edit_service(
    request: Request,
    u_id: str = Body(...),
    name: Any = Body(UNSET),
    description: Any = Body(UNSET),
    creation_date: Any = Body(UNSET),
    price_main: Any = Body(UNSET),
    discount_value: Any = Body(UNSET),
    discount_date: Any = Body(UNSET),
    status: Any = Body(UNSET),
    left: Any = Body(UNSET),
    sell_time: Any = Body(UNSET),
    oferta_limit: Any = Body(UNSET),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    current = PaymentServiceDB.get_service(u_id)
    if not current:
        raise HTTPException(status_code=404, detail="Service not found")

    patch: dict = {}
    if name is not UNSET:
        patch["name"] = name
    if description is not UNSET:
        patch["description"] = description
    if creation_date is not UNSET:
        patch["creation_date"] = creation_date
    if price_main is not UNSET:
        patch["price_main"] = price_main
    if discount_value is not UNSET:
        patch["discount_value"] = discount_value
    if discount_date is not UNSET:
        patch["discount_date"] = discount_date
    if status is not UNSET:
        patch["status"] = status
    if left is not UNSET:
        patch["left"] = left
    if sell_time is not UNSET:
        patch["sell_time"] = sell_time
    if oferta_limit is not UNSET:
        patch["oferta_limit"] = bool(oferta_limit)

    if not patch:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    if "discount_value" in patch:
        try:
            dv = int(patch["discount_value"])
        except Exception:
            raise HTTPException(status_code=400, detail="discount_value must be int")
        if dv < 0 or dv > 100:
            raise HTTPException(
                status_code=400, detail="discount_value must be in [0, 100]"
            )

    if "left" in patch and patch["left"] is not None:
        try:
            lf = int(patch["left"])
        except Exception:
            raise HTTPException(status_code=400, detail="left must be int or null")
        if lf < 0:
            raise HTTPException(status_code=400, detail="left must be >= 0")

    merged = current.to_dict()
    merged.update(patch)

    try:
        updated = ServiceModel.from_dict(merged)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid service data: {e}")

    changes = []

    def add_change(field: str, old, new):
        if old != new:
            changes.append(f"{field}: {old} → {new}")

    add_change("name", current.name, updated.name)
    if current.description != updated.description:
        changes.append("description: (updated)")

    add_change("status", current.status, updated.status)
    add_change("left", current.left, updated.left)
    add_change("price_main", current.price_main, updated.price_main)
    add_change("discount_value", current.discount_value, updated.discount_value)
    add_change("discount_date", current.discount_date, updated.discount_date)
    add_change("sell_time", current.sell_time, updated.sell_time)
    add_change("creation_date", current.creation_date, updated.creation_date)
    add_change("oferta_limit", current.oferta_limit, updated.oferta_limit)

    PaymentServiceDB.upsert_service(u_id, updated)

    LogDB.add_log(
        LogType.SERVICE_UPDATE,
        f"Service {u_id} "
        + (
            "edited:\n" + "\n".join(changes)
            if changes
            else "edit attempted with no changes"
        ),
        username,
    )

    return {"success": True}
