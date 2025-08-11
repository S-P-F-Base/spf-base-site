from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/get")
def get_service(
    request: Request,
    u_id: str = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    svc = PaymentServiceDB.get_service(u_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    return {"u_id": u_id, "data": svc.to_dict(), "final_price": f"{svc.price():.2f}"}
