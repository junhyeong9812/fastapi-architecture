"""배송 도메인 Port 정의."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from app.shared.value_objects import Money


@dataclass(frozen=True)
class ShippingFeeResult:
    """배송비 계산 결과."""
    fee: Money              # 실제 배송비 (할인 후)
    original_fee: Money     # 할인 전 기본 배송비
    discount_type: str      # "none", "basic_half", "premium_free"
    reason: str             # 사람이 읽을 수 있는 사유


class ShippingFeePolicy(Protocol):
    """배송비 정책 인터페이스. DI가 구독 등급에 따라 구현체를 주입."""
    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult: ...


class ShipmentRepositoryProtocol(Protocol):
    async def save(self, shipment: object) -> None: ...
    async def find_by_id(self, shipment_id: UUID) -> object | None: ...
    async def find_by_order_id(self, order_id: UUID) -> object | None: ...
    async def update(self, shipment: object) -> None: ...