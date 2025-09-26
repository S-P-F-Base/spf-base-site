from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB

from .base_func import CommissionKey, PaymentStatus

router = APIRouter()


@router.post("/edit")
def edit_payment(
    request: Request,
    u_id: str = Body(...),
    status: PaymentStatus | None = Body(None),
    player_id: str | None = Body(None),
    commission_key: CommissionKey | None = Body(None),
):
    return 404

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    changes: list[str] = []

    if status is not None and pay.status == "done" and status != "cancelled":
        raise HTTPException(
            status_code=400, detail="Cannot change status of a completed payment"
        )

    old_status = pay.status

    if status is not None and status != pay.status:
        changes.append(f"status: {pay.status} → {status}")

        if old_status == "pending" and status in ("cancelled", "declined"):
            restored = 0
            for snap in pay.snapshot:
                svc_id = getattr(snap, "service_u_id", None)
                if svc_id:
                    PaymentServiceDB.increment_service_left(svc_id, 1)
                    restored += 1
            if restored:
                changes.append(f"restored {restored} item(s) stock")

        pay.status = status

    if player_id is not None and player_id != pay.player_id:
        changes.append(f"player_id: {pay.player_id} → {player_id}")
        pay.player_id = player_id

    if commission_key is not None and commission_key != pay.commission_key:
        changes.append(f"commission_key: {pay.commission_key} → {commission_key}")
        pay.commission_key = commission_key

    PaymentServiceDB.upsert_payment(u_id, pay)

    return {"success": True, "total": f"{pay.total():.2f}"}
