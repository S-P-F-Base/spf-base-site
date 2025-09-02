from fastapi import APIRouter, HTTPException, Request

from data_bases import PaymentServiceDB, UserAccess, UserDB
from data_control import req_authorization

router = APIRouter()


@router.get("/list")
def list_payments(request: Request):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PAYMENT):
        raise HTTPException(status_code=403, detail="Insufficient access")

    rows = PaymentServiceDB.list_payments()
    out = []
    for u_id, pay in rows:
        out.append(
            {
                "u_id": u_id,
                "status": pay.status,
                "player_id": pay.player_id,
                "commission_key": pay.commission_key,
                "snapshot_len": len(pay.snapshot),
                "total": f"{pay.total():.2f}",
                "tax_check_id": pay.tax_check_id,
                "received_amount": f"{pay.received_amount:.2f}"
                if pay.received_amount is not None
                else None,
                "payer_amount": f"{pay.payer_amount:.2f}"
                if pay.payer_amount is not None
                else None,
            }
        )
    return out
