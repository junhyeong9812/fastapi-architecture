"""주문 엔티티.

★ 핵심 학습 포인트:
이 파일에 import fastapi / import sqlalchemy가 없다!
도메인 로직은 프레임워크를 모른다. 이것이 Hexagonal Architecture의 핵심.

Order.create()는 팩토리 메서드 패턴.
__init__ 대신 create()를 사용하여 생성 규칙(검증)을 강제한다.
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.shared.value_objects import Money
from app.orders.domain.value_objects import  OrderStatus
from app.orders.domain.exceptions import InvalidOrderError, InvalidStatusTransition


@dataclass
class OrderItem:
    """주문 항목. 하나의 상품 + 수량 + 단가."""
    product_name: str
    quantity: int
    unit_price: Money       # Money 값 객체 사용

    @property
    def subtotal(self) -> Money:
        """소계 = 단가 × 수량. 주문 총액 계산에 사용."""
        return self.unit_price.multiply(self.quantity)


@dataclass
class Order:
    """주문 엔티티 (Aggregate Root).

    Aggregate Root: 이 엔티티를 통해서만 OrderItem에 접근한다.
    외부에서 OrderItem을 직접 수정하지 않고, Order의 메서드를 통해서만 변경.
    """
    id: UUID
    customer_name: str
    items: list[OrderItem]
    status: OrderStatus
    total_amount: Money
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, customer_name: str, items: list[OrderItem]) -> "Order":
        """팩토리 메서드. 생성 규칙을 강제한다.

        ★ 왜 __init__ 대신 create()를 쓰는가?
        DB에서 로드할 때는 검증 없이 그대로 복원해야 한다.
        새로 생성할 때만 검증이 필요하므로 별도 팩토리 메서드로 분리.
        """
        # 규칙 1: 고객 이름 필수
        if not customer_name or not customer_name.strip():
            raise InvalidOrderError("고객 이름이 비어있습니다")

        # 규칙 2: 최소 1개 항목
        if not items:
            raise InvalidOrderError("주문 항목이 비어있습니다")

        # 규칙 3: 각 항목의 수량 > 0, 가격 > 0
        for item in items:
            if item.quantity <= 0:
                raise InvalidOrderError(f"수량이 0 이하입니다: {item.product_name}")
            if not item.unit_price.is_positive:
                raise InvalidOrderError(f"가격이 0 이하입니다: {item.product_name}")

        # 총액 자동 계산: 모든 항목의 소계(subtotal) 합산
        total = items[0].subtotal
        for item in items[1:]:
            total = total.add(item.subtotal)

        now = datetime.now(UTC)
        return cls(
            id=uuid4(),                     # UUID 자동 생성
            customer_name=customer_name.strip(),
            items=items,
            status=OrderStatus.CREATED,     # 초기 상태: CREATED
            total_amount=total,
            created_at=now,
            updated_at=now,
        )

    def _transition_to(self, target: OrderStatus) -> None:
        """상태 전이 공통 로직. 규칙 위반 시 예외 발생."""
        if not self.status.can_transition_to(target):
            raise InvalidStatusTransition(self.status.value, target.value)
        self.status = target
        self.updated_at = datetime.now(UTC)

    def mark_payment_pending(self) -> None:
        """CREATED → PAYMENT_PENDING. 주문 생성 직후 호출."""
        self._transition_to(OrderStatus.PAYMENT_PENDING)

    def mark_paid(self) -> None:
        """PAYMENT_PENDING → PAID. 결제 승인 이벤트 수신 시 호출."""
        self._transition_to(OrderStatus.PAID)

    def mark_shipping(self) -> None:
        """PAID → SHIPPING. 배송 생성 이벤트 수신 시 호출."""
        self._transition_to(OrderStatus.SHIPPING)

    def mark_delivered(self) -> None:
        """SHIPPING → DELIVERED. 배송 완료 이벤트 수신 시 호출."""
        self._transition_to(OrderStatus.DELIVERED)

    def cancel(self) -> None:
        """→ CANCELLED. CREATED 또는 PAYMENT_PENDING에서만 가능."""
        self._transition_to(OrderStatus.CANCELLED)