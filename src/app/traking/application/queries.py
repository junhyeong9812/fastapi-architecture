from dataclasses import dataclass


@dataclass(frozen=True)
class GetOrderTrackingQuery:
    order_id: str