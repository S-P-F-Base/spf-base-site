from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_bases import (
    Service as ServiceModel,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/edit")
def edit_service(
    request: Request,
    u_id: str = Body(...),
    data: dict = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    current = PaymentServiceDB.get_service(u_id)
    if not current:
        raise HTTPException(status_code=404, detail="Service not found")

    merged = current.to_dict()
    merged.update(data)

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

    PaymentServiceDB.upsert_service(u_id, updated)

    if changes:
        LogDB.add_log(
            LogType.SERVICE_UPDATE,
            f"Service {u_id} edited:\n" + "\n".join(changes),
            username,
        )
    else:
        LogDB.add_log(
            LogType.SERVICE_UPDATE,
            f"Service {u_id} edit attempted with no changes",
            username,
        )

    return {"success": True}
