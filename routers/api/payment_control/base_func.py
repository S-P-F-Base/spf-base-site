from typing import Literal

from data_bases import PaymentServiceDB, ServiceSnapshot
from data_bases import Service as ServiceModel

PaymentStatus = Literal["pending", "declined", "cancelled", "done"]
CommissionKey = Literal["PC", "AC"]


def build_snapshots(items: list[dict]) -> list[ServiceSnapshot]:
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    want: dict[str, int] = {}
    for entry in items:
        svc_id = entry.get("service_u_id")
        qty = int(entry.get("qty", 1))
        if not svc_id:
            raise ValueError("service_u_id is required for each item")
       
        if qty <= 0:
            raise ValueError(f"qty must be >= 1 for {svc_id}")
        
        want[svc_id] = want.get(svc_id, 0) + qty

    cache: dict[str, ServiceModel] = {}
    for svc_id, qty in want.items():
        svc = PaymentServiceDB.get_service(svc_id)
        if not svc:
            raise ValueError(f"Service not found: {svc_id}")

        if svc.status != "on":
            raise ValueError(f"Service is not active: {svc_id}")

        if svc.left is not None and svc.left < qty:
            raise ValueError(
                f"Not enough stock for {svc_id}: need {qty}, left {svc.left}"
            )

        cache[svc_id] = svc

    decremented: list[tuple[str, int]] = []
    try:
        for svc_id, qty in want.items():
            if not PaymentServiceDB.decrement_service_left(svc_id, qty):
                raise ValueError(f"Failed to decrement stock for {svc_id}")
            decremented.append((svc_id, qty))

    except Exception:
        for svc_id, qty in reversed(decremented):
            PaymentServiceDB.increment_service_left(svc_id, qty)

        raise

    snapshots: list[ServiceSnapshot] = []
    for svc_id, qty in want.items():
        svc = cache[svc_id]
        for _ in range(qty):
            snapshots.append(
                ServiceSnapshot(
                    name=svc.name,
                    creation_date=svc.creation_date,
                    price_main=svc.price_main,
                    discount_value=svc.discount_value,
                    service_u_id=svc_id,
                )
            )

    return snapshots
