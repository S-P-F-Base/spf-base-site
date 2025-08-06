from fastapi import APIRouter, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentDB,
    UserAccess,
    UserDB,
)
from data_control import req_authorization,BaseUUIDAPIData

router = APIRouter()


@router.post("/delete")
def delete(request: Request, data: BaseUUIDAPIData):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    service = PaymentDB.services.get_by_u_id(data.uuid)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    success = PaymentDB.services.delete(data.uuid)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete service")

    LogDB.add_log(
        LogType.SERVICE_DELETE,
        f"Deleted service {service['meta'].name}",  # type: ignore
        username,
    )
    return 200
