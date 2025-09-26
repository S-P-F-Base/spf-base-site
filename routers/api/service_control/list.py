from fastapi import APIRouter, Request

from data_bases import PaymentServiceDB

router = APIRouter()


@router.get("/list")
def list_services(request: Request):
    return 404

    rows = PaymentServiceDB.list_services()
    return [
        {"u_id": u, "data": svc.to_dict(), "final_price": f"{svc.price():.2f}"}
        for (u, svc) in rows
    ]
