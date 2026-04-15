"""주문 도메인의 값 객체(Value Object).

★ 학습 포인트:
- Money는 불변 값 객체. 모든 연산이 새 인스턴스를 반환한다.
  원본은 절대 변경되지 않는다 (함수형 프로그래밍의 핵심 원칙).
- OrderStatus는 상태 머신. can_transition_to()로 허용된 전이만 가능하다.
- 이 파일에 import fastapi, import sqlalchemy가 없다!
  도메인 로직은 프레임워크를 모른다. 이것이 Hexagonal Architecture의 핵심.
"""

from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    """주문 상태 열거형.

    str을 상속하는 이유: JSON 직렬화 시 자동으로 문자열로 변환.
    DB에도 문자열로 저장된다 ("created", "paid" 등).
    """
    CREATED = "created"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """이 상태에서 target 상태로 전이 가능한지 확인.
        _VALID_TRANSITIONS 딕셔너리에 정의된 규칙을 참조한다.
        """
        return target in _VALID_TRANSITIONS.get(self, set())


# 상태 전이 규칙 정의
# set()은 빈 집합 = 어디로도 전이 불가 (종료 상태)
_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED},
    OrderStatus.PAYMENT_PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPING},           # ★ PAID에서 CANCELLED 불가!
    OrderStatus.SHIPPING: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),                        # 종료 상태
    OrderStatus.CANCELLED: set(),                        # 종료 상태
}