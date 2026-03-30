"""Command DTO — 쓰기 의도를 표현한다.

★ CQRS 포인트:
Command = "이렇게 해줘" (상태 변경 요청)
Query = "이것 좀 보여줘" (데이터 조회 요청)
Command와 Query를 분리하면 각각 독립적으로 최적화할 수 있다.

DTO는 단순 데이터 운반 객체. 비즈니스 로직 없음.
frozen=True: 생성 후 변경 불가 (안전한 데이터 전달).
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderItemDTO:
    """주문 항목 데이터. Router에서 Handler로 전달될 때 사용."""
    product_name: str
    quantity: int
    unit_price: Decimal     # Pydantic의 float → Decimal 변환은 Router에서


@dataclass(frozen=True)
class CreateOrderCommand:
    """주문 생성 명령."""
    customer_name: str
    items: list[OrderItemDTO]


@dataclass(frozen=True)
class CancelOrderCommand:
    """주문 취소 명령."""
    order_id: str