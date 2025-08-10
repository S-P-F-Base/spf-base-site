import uuid

from fastapi import APIRouter, Body, HTTPException, Request

from data_bases import (
    LogDB,
    LogType,
    PaymentServiceDB,
    UserAccess,
    UserDB,
)
from data_bases import (
    Service as ServiceModel,
)
from data_control import req_authorization

router = APIRouter()


@router.post("/create")
def create_service(
    request: Request,
    data: dict = Body(...),
):
    username = req_authorization(request)
    if not UserDB.has_access(username, UserAccess.SERVICE_CONTROL):
        raise HTTPException(status_code=403, detail="Insufficient access")

    u_id = uuid.uuid4().hex

    try:
        svc = ServiceModel.from_dict(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid service data: {e}")

    PaymentServiceDB.upsert_service(u_id, svc)
    LogDB.add_log(
        LogType.SERVICE_CREATE, f"Service created {u_id} ({svc.name})", username
    )
    return {"u_id": u_id}
