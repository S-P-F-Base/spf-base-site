import json
from pathlib import Path

from fastapi import APIRouter, Request

import utils.admin
from templates import templates

router = APIRouter()


def load_currency_series() -> dict[str, list[tuple[str, int]]]:
    series: dict[str, list[tuple[str, int]]] = {}
    snaps = sorted((Path("data/snapshots")).glob("inv_*.json"))

    for snap in snaps:
        ts = snap.stem.split("_", 1)[1]
        with snap.open(encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("inventory", []):
            iid, cnt = item.get("id"), int(item.get("count", 0))
            if not iid:
                continue

            if not (iid.startswith("currency_") or iid.startswith("ammo_")):
                continue

            series.setdefault(iid, []).append((ts, cnt))

    for iid in series:
        series[iid].sort(key=lambda p: p[0])

    return series


@router.get("/economy")
def economy(request: Request):
    utils.admin.require_access(request, "panel_access")

    series = load_currency_series()
    return templates.TemplateResponse(
        "economy.html", {"request": request, "series": series}
    )
