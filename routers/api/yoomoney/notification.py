import hashlib

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from database import Config, YoomoneyDB

router = APIRouter()


@router.post("/notification", response_class=PlainTextResponse)
def yoomoney_notification(
    request: Request,
    notification_type: str = Form(...),
    operation_id: str = Form(...),
    amount: str = Form(...),
    currency: str = Form(...),
    datetime: str = Form(...),
    sender: str = Form(...),
    codepro: str = Form(...),
    sha1_hash: str = Form(...),
    label: str = Form(""),
    withdraw_amount: str = Form(""),
):
    check_string = "&".join(
        [
            notification_type,
            operation_id,
            amount,
            currency,
            datetime,
            sender,
            codepro,
            Config.yoomoney_notification(),
            label,
        ]
    )

    calculated_hash = hashlib.sha1(check_string.encode("utf-8")).hexdigest()

    if calculated_hash != sha1_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid hash",
        )

    try:
        payment_id = int(label)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid label format")

    payment = YoomoneyDB.get_payment_by_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    recive = amount if YoomoneyDB.USER_PAYS_COMMISSION else withdraw_amount

    YoomoneyDB.update_payment(
        id=payment_id,
        status="auto",
        receive=float(recive),
        type_of_receive="add",
    )

    return "OK"
