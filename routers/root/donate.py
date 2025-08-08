from fastapi import APIRouter, HTTPException, Request

from templates import templates

router = APIRouter()


@router.get("/donate")
def donate(request: Request):
    raise HTTPException(404)

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
