from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB

router = APIRouter()


@router.post("/delete")
def delete_payment(
    request: Request,
    u_id: str = Body(..., embed=True),
):
    return 404

    pay = PaymentServiceDB.get_payment(u_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")

    if pay.status == "pending":
        restored = 0
        for snap in pay.snapshot:
            svc_id = getattr(snap, "service_u_id", None)
            if svc_id:
                PaymentServiceDB.increment_service_left(svc_id, 1)
                restored += 1

    ok = PaymentServiceDB.delete_payment(u_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete payment")

    return {"success": True}
