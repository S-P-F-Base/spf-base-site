import uuid

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import Payment as PaymentModel
from data_bases import PaymentServiceDB

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
    return 404

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

    return {"success": True, "u_id": u_id, "total": f"{pay.total():.2f}"}
