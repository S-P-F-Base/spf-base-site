from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/delete")
def delete_service(request: Request, u_id: str = Body(...)):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    svc = PaymentServiceDB.get_service(u_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    ok = PaymentServiceDB.delete_service(u_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete service")

    LogDB.add_log(
        LogType.SERVICE_DELETE, f"Service deleted {u_id} '{svc.name}'", username
    )
    return {"success": True}
