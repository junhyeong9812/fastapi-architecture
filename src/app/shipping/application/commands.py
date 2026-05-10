from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateShipmentStatusCommand:
    """배송 상태 수동 변경. 시뮬레이션용."""
    shipment_id: str
    new_status: str             # "in_transit", "delivered"
    tracking_number: str | None = None