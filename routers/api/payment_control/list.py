from fastapi import APIRouter, Request

from data_bases import PaymentServiceDB

router = APIRouter()


@router.get("/list")
def list_payments(request: Request):
    return 404

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
