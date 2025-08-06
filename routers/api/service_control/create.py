from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentDB,
    ServiceMeta,
    ServiceStatus,
    UserAccess,
    UserDB,
)
from data_control import ServiceCreateAPIData, req_authorization

router = APIRouter()


@router.post("/create")
def create(request: Request, data: ServiceCreateAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    meta = ServiceMeta(
        name=data.name,
        description=data.description,
        limit=data.limit,
        price_main=Decimal(data.price_main),
        sell_time_end=data.sell_time_end,
    )

    if data.discount or data.discount_time_end:
        meta.set_discount(data.discount, data.discount_time_end)

    PaymentDB.services.append(meta, ServiceStatus.ACTIVE)
    LogDB.add_log(LogType.SERVICE_CREATE, f"Created service {data.name}", username)

    return 200
