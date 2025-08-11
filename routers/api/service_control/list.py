from fastapi import APIRouter, HTTPException, Request

from data_bases import (
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization

router = APIRouter()


@router.get("/list")
def list_services(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    rows = PaymentServiceDB.list_services()
    return [
        {"u_id": u, "data": svc.to_dict(), "final_price": f"{svc.price():.2f}"}
        for (u, svc) in rows
    ]
