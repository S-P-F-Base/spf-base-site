import hashlib
from decimal import Decimal

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from data_bases import LogDB, LogType
from data_control import AutoTax, Config

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

    payment_id = label
    payment = PaymentDB.payments.get_by_u_id(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    service = PaymentDB.services.get_by_u_id(payment.what_buy)
    payment.received = Decimal(amount)
    payment.user_pay = Decimal(withdraw_amount)
    payment_status = payment.update_status()

    if service:
        services_meta = service.get("meta")
        if (
            isinstance(services_meta, ServiceMeta)
            and payment_status == PaymentStatus.done
            and not payment.tax_check_id
        ):
            try:
                tax_id = AutoTax.post_income(
                    [(services_meta.name, services_meta.price)]
                )
                payment.tax_check_id = tax_id

            except Exception as e:
                LogDB.add_log(
                    LogType.PAY_RESIVE,
                    f"Failed to send tax receipt: {e}",
                    "Yoomoney notification",
                )

    PaymentDB.payments.edit(payment_id, payment)

    LogDB.add_log(
        LogType.PAY_RESIVE,
        f"Confirmation of payment: {payment_id}",
        "Yoomoney notification",
    )

    return 200
