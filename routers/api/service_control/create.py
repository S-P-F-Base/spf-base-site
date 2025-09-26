import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB
from data_bases import Service as ServiceModel

router = APIRouter()


@router.post("/create")
def create_service(
    request: Request,
    name: str = Body(...),
    description: str = Body(""),
    price_main: str = Body(...),
    discount_value: int = Body(0),
    discount_date: str | None = Body(None),
    status: Literal["on", "off", "archive"] = Body("off"),
    left: int | None = Body(None),
    sell_time: str | None = Body(None),
    oferta_limit: bool = Body(False),
):
    return 404

    if discount_value < 0 or discount_value > 100:
        raise HTTPException(
            status_code=400, detail="discount_value must be in [0, 100]"
        )

    if left is not None and left < 0:
        raise HTTPException(status_code=400, detail="left must be >= 0")

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

    u_id = uuid.uuid4().hex

    try:
        svc = ServiceModel.from_dict(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid service data: {e}")

    PaymentServiceDB.upsert_service(u_id, svc)

    return {"u_id": u_id}
