from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import PaymentServiceDB

router = APIRouter()


@router.post("/delete")
def delete_service(
    request: Request,
    u_id: str = Body(..., embed=True),
):
    return 404

    svc = PaymentServiceDB.get_service(u_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    ok = PaymentServiceDB.delete_service(u_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete service")

    return {"success": True}
