import uuid

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_bases import Payment as PaymentModel
from data_control import req_authorization

from .base_func import CommissionKey, PaymentStatus, build_snapshots

router = APIRouter()


@router.post("/create")
def create_payment(
    request: Request,
    player_id: str = Body(...),
    items: list[dict] = Body(...),
    commission_key: CommissionKey = Body("AC"),
    status: PaymentStatus = Body("pending"),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.CONTROL_PAYMENT):
        raise HTTPException(status_code=403, detail="Insufficient access")

    try:
        snapshots = build_snapshots(items)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    pay = PaymentModel(
        status=status,
        player_id=player_id,
        snapshot=snapshots,
        commission_key=commission_key,
        tax_check_id=None,
        received_amount=None,
        payer_amount=None,
    )

    u_id = uuid.uuid4().hex
    PaymentServiceDB.upsert_payment(u_id, pay)

    LogDB.add_log(
        LogType.PAYMENT_CREATE,
        f"Payment created {u_id} for player {player_id} items={len(snapshots)} total={pay.total():.2f}",
        username,
    )
    return {"success": True, "u_id": u_id, "total": f"{pay.total():.2f}"}
