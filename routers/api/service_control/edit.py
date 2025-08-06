from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentDB,
    ServiceMeta,
    UserAccess,
    UserDB,
)
from data_control import ServiceEditAPIData, req_authorization

router = APIRouter()


@router.post("/edit")
def edit(request: Request, data: ServiceEditAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    service = PaymentDB.services.get_by_u_id(data.uuid)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    old_meta: ServiceMeta = service["meta"]  # type: ignore
    status = service["status"] if data.status is None else data.status

    meta = ServiceMeta(
        name=data.name if data.name is not None else old_meta.name,
        description=data.description
        if data.description is not None
        else old_meta.description,
        limit=data.limit if data.limit is not None else old_meta.limit,
        price_main=Decimal(data.price_main)
        if data.price_main is not None
        else old_meta.price_main,
        sell_time_end=data.sell_time_end
        if data.sell_time_end is not None
        else old_meta.sell_time_end,
    )

    if data.discount is not None or data.discount_time_end is not None:
        meta.set_discount(
            data.discount if data.discount is not None else old_meta._discount,
            data.discount_time_end
            if data.discount_time_end is not None
            else old_meta._discount_time_end,
        )
    else:
        meta.set_discount(old_meta._discount, old_meta._discount_time_end)

    success = PaymentDB.services.edit(data.uuid, meta, status)  # type: ignore
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update service")

    changes = []

    def add_diff(field: str, old, new):
        if old != new:
            changes.append(f'{field}="{old}"→"{new}"')

    add_diff("name", old_meta.name, meta.name)
    add_diff("description", old_meta.description, meta.description)
    add_diff("price_main", old_meta.price_main, meta.price_main)
    add_diff("limit", old_meta.limit, meta.limit)
    add_diff("sell_time_end", old_meta.sell_time_end, meta.sell_time_end)
    add_diff("discount", old_meta._discount, meta._discount)
    add_diff("discount_time_end", old_meta._discount_time_end, meta._discount_time_end)
    if data.status is not None and data.status != service["status"]:
        add_diff("status", service["status"], data.status)

    changes_str = ", ".join(changes) if changes else "no visible changes"

    LogDB.add_log(
        LogType.SERVICE_UPDATE,
        f'Edited service "{old_meta.name}": {changes_str}',
        username,
    )

    return 200
