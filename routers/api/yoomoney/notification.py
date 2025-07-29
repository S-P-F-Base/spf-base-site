import hashlib
from decimal import Decimal

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from data_bases import LogDB, LogType, PaymentDB
from data_control import Config

router = APIRouter()


@router.post("/notification", response_class=PlainTextResponse)
def yoomoney_notification(
    request: Request,
    notification_type: str = Form(...),  # Не важно для бд
    operation_id: str = Form(...),  # Не важно для бд
    currency: str = Form(...),  # Не важно для бд
    sender: str = Form(...),  # Не важно для бд
    codepro: str = Form(...),  # Не важно для бд
    sha1_hash: str = Form(...),  # Не важно для бд
    label: str = Form(""),
    datetime: str = Form(...),
    withdraw_amount: str = Form(""),  # Сумма перевёл юзер
    amount: str = Form(...),  # Сумма зачислена
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
        payment_id = label

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid label format")

    payment = PaymentDB.payments.get_by_u_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.received = Decimal(amount)
    payment.user_pay = Decimal(withdraw_amount)
    payment.update_status()

    PaymentDB.payments.edit(payment_id, payment)

    LogDB.add_log(
        LogType.PAY_RESIVE,
        f"Confirmation of payment: {payment_id}",
        "Yoomoney notification",
    )

    return 200
