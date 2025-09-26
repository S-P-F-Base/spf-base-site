from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB

router = APIRouter()


@router.post("/get")
def get_service(
    request: Request,
    u_id: str = Body(..., embed=True),
):
    return 404

    svc = PaymentServiceDB.get_service(u_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    return {"u_id": u_id, "data": svc.to_dict(), "final_price": f"{svc.price():.2f}"}
