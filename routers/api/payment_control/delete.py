from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/delete")
def delete_payment(
    request: Request,
    u_id: str = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PAYMENT):
        raise HTTPException(status_code=403, detail="Insufficient access")

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    ok = PaymentServiceDB.delete_payment(u_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete payment")

    LogDB.add_log(
        LogType.PAYMENT_DELETE,
        f"Payment deleted {u_id} (player {pay.player_id}) total={pay.total():.2f}",
        username,
    )
    return {"success": True}
