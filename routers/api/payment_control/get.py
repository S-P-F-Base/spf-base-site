from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.post("/get")
def get_payment(
    request: Request,
    u_id: str = Body(..., embed=True),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PAYMENT):
        raise HTTPException(status_code=403, detail="Insufficient access")

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "u_id": u_id,
        "status": pay.status,
        "player_id": pay.player_id,
        "commission_key": pay.commission_key,
        "snapshot": [s.to_dict() for s in pay.snapshot],
        "total": f"{pay.total():.2f}",
        "tax_check_id": pay.tax_check_id,
        "received_amount": f"{pay.received_amount:.2f}"
        if pay.received_amount is not None
        else None,
        "payer_amount": f"{pay.payer_amount:.2f}"
        if pay.payer_amount is not None
        else None,
    }
