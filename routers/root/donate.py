from fastapi import APIRouter, Request

from data_bases import DonateDB, DonateStatus
from templates import templates

router = APIRouter()


@router.get("/donate")
def donate(request: Request):
    donate_variants = DonateDB.get_donates(DonateStatus.NO_STOCK | DonateStatus.ACTIVE)

    active_list = []
    no_stock_list = []

    for entry in donate_variants:
        entry["meta"].recalculate_discount()

        if entry["status"] & DonateStatus.NO_STOCK:
            no_stock_list.append(entry)
            continue

        if entry["status"] & DonateStatus.ACTIVE:
            active_list.append(entry)

    return templates.TemplateResponse(
        "donate.html",
        {
            "request": request,
            "active_list": active_list,
            "no_stock_list": no_stock_list,
        },
    )
