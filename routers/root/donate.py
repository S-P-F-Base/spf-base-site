from datetime import datetime, timedelta
from decimal import Decimal
from random import choice, randint

from fastapi import APIRouter, Request

from data_bases import PaymentDB, ServiceMeta, ServiceStatus
from templates import templates

router = APIRouter()


@router.get("/donate")
def donate(request: Request):
    test_mode = request.query_params.get("test") is not None

    if test_mode:
        active_list, no_stock_list = generate_fake_donates()
    else:
        donate_variants = PaymentDB.services.get_by_status(
            ServiceStatus.NO_STOCK | ServiceStatus.ACTIVE
        )

        active_list = []
        no_stock_list = []

        for entry in donate_variants:
            entry["meta"].recalculate_discount()

            if entry["status"] & ServiceStatus.NO_STOCK:
                no_stock_list.append(entry)
                continue

            if entry["status"] & ServiceStatus.ACTIVE:
                active_list.append(entry)

    return templates.TemplateResponse(
        "donate.html",
        {
            "request": request,
            "active_list": active_list,
            "no_stock_list": no_stock_list,
        },
    )


def generate_fake_donates():
    names = [
        "VIP-доступ",
        "Премиум-подписка",
        "Эксклюзивный скин оружия",
        "Улучшение характеристик",
        "Доступ к закрытой зоне",
    ]

    descriptions = [
        "Приоритетный вход на сервер и уникальные возможности.",
        "Расширенный функционал и бонусы для активных игроков.",
        "Выделяйся с уникальным дизайном своего оружия.",
        "Повышай свои игровые показатели и возможности.",
        "Открой для себя новые локации и эксклюзивный контент.",
    ]

    def make_entry(i: int, active=True):
        discount = choice([0, 10, 25, 50])
        discount_end = (
            datetime.now() + timedelta(minutes=randint(1, 20), hours=randint(0, 48))
            if discount > 0
            else None
        )
        limit = choice([None, randint(1, 25)]) if active else choice([None, 0])
        price = Decimal(randint(50, 500))

        meta = ServiceMeta(
            name=f"{choice(names)}",
            description=choice(descriptions),
            limit=limit,
            price_main=price,
        )
        meta.set_discount(discount, discount_end)

        return {
            "uuid": f"test_{i}",
            "meta": meta,
            "status": ServiceStatus.ACTIVE if active else ServiceStatus.NO_STOCK,
        }

    active_list = [make_entry(i) for i in range(1, 6)]
    no_stock_list = [make_entry(i + 100, active=False) for i in range(1, 3)]

    return active_list, no_stock_list
