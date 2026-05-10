"""배송 엔티티."""

from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from app.shared.value_objects import Money


@dataclass(frozen=True)
class Address:
    """배송 주소 값 객체."""
    street: str
    city: str
    zip_code: str


class ShipmentStatus(str, Enum):
    PREPARING = "preparing"     # 배송 준비중
    IN_TRANSIT = "in_transit"   # 배송중
    DELIVERED = "delivered"     # 배송 완료


class ShipmentError(Exception):
    pass


@dataclass
class Shipment:
    id: UUID
    order_id: UUID
    status: ShipmentStatus
    address: Address
    shipping_fee: Money         # 실제 배송비 (할인 후)
    original_fee: Money         # 할인 전 배송비
    fee_discount_type: str
    tracking_number: str | None
    estimated_delivery: datetime | None

    @classmethod
    def create(
        cls, order_id: UUID, address: Address,
        shipping_fee: Money, original_fee: Money,
        fee_discount_type: str,
    ) -> "Shipment":
        return cls(
            id=uuid4(), order_id=order_id,
            status=ShipmentStatus.PREPARING,
            address=address, shipping_fee=shipping_fee,
            original_fee=original_fee,
            fee_discount_type=fee_discount_type,
            tracking_number=None, estimated_delivery=None)

    def mark_in_transit(self, tracking_number: str) -> None:
        """PREPARING → IN_TRANSIT. 운송장 번호와 함께."""
        if self.status != ShipmentStatus.PREPARING:
            raise ShipmentError(f"PREPARING이 아닌 배송은 발송 불가: {self.status}")
        self.status = ShipmentStatus.IN_TRANSIT
        self.tracking_number = tracking_number

    def mark_delivered(self) -> None:
        """IN_TRANSIT → DELIVERED."""
        if self.status != ShipmentStatus.IN_TRANSIT:
            raise ShipmentError(f"IN_TRANSIT이 아닌 배송은 완료 불가: {self.status}")
        self.status = ShipmentStatus.DELIVERED