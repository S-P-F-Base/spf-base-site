from typing import Literal

from data_bases import PaymentServiceDB, ServiceSnapshot
from data_bases import Service as ServiceModel

PaymentStatus = Literal["pending", "declined", "cancelled", "done"]
CommissionKey = Literal["PC", "AC"]


def build_snapshots(items: list[dict]) -> list[ServiceSnapshot]:
    snapshots: list[ServiceSnapshot] = []

    for entry in items:
        svc_id = entry.get("service_u_id")
        qty = int(entry.get("qty", 1))
        if not svc_id:
            raise ValueError("service_u_id is required for each item")
        if qty <= 0:
            raise ValueError(f"qty must be >= 1 for {svc_id}")

        svc: ServiceModel | None = PaymentServiceDB.get_service(svc_id)
        if not svc:
            raise ValueError(f"Service not found: {svc_id}")

        for _ in range(qty):
            snapshots.append(
                ServiceSnapshot(
                    name=svc.name,
                    creation_date=svc.creation_date,
                    price_main=svc.price_main,
                    discount_value=svc.discount_value,
                )
            )
    return snapshots
