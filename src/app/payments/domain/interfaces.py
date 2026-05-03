from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from app.shared.value_objects import Money


@dataclass(frozen=True)
class DiscountResult:
    """할인 계산 결과."""
    discount_amount: Money      # 할인 금액
    discount_type: str          # "none", "basic_subscription", "premium_subscription"


class DiscountPolicy(Protocol):
    """할인 정책 인터페이스.
    구현체: NoDiscountPolicy, SubscriptionDiscountPolicy.
    """
    def calculate_discount(self, amount: Money) -> DiscountResult: ...


@dataclass(frozen=True)
class GatewayResult:
    """PG(결제 게이트웨이) 응답."""
    success: bool
    transaction_id: str | None
    message: str


class PaymentGatewayProtocol(Protocol):
    """PG 인터페이스. 구현체: FakePaymentGateway."""
    async def process(self, payment: object) -> GatewayResult: ...


class PaymentRepositoryProtocol(Protocol):
    """결제 저장소 인터페이스."""
    async def save(self, payment: object) -> None: ...
    async def find_by_id(self, payment_id: UUID) -> object | None: ...
    async def find_by_order_id(self, order_id: UUID) -> object | None: ...