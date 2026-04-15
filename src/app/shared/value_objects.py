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

class Money:
    """돈을 표현하는 값 객체.

    __slots__: 메모리 최적화. 지정된 속성만 가질 수 있다.
    불변성을 강제하진 않지만, 모든 연산이 새 인스턴스를 반환하는 규약.
    """
    __slots__ = ("amount", "currency")

    def __init__(self, amount: Decimal, currency: str = "KRW") -> None:
        if amount < 0:
            raise ValueError("금액은 음수일 수 없습니다")
        # object.__setattr__를 쓰지 않는 이유: __slots__만으로 충분
        self.amount = amount
        self.currency = currency

    def _check_currency(self, other: "Money") -> None:
        """통화가 다르면 연산 불가. KRW끼리만, USD끼리만 연산 가능."""
        if self.currency != other.currency:
            raise ValueError(f"통화가 다릅니다: {self.currency} vs {other.currency}")

    def add(self, other: "Money") -> "Money":
        """더하기. 원본은 변경하지 않고 새 Money를 반환."""
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """빼기. 할인 적용 시 사용: 원래가격.subtract(할인금액)."""
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, quantity: int) -> "Money":
        """수량 곱하기. 단가 × 수량 = 소계."""
        return Money(self.amount * quantity, self.currency)

    def apply_rate(self, rate: Decimal) -> "Money":
        """비율 적용. 10% 할인 → rate=Decimal("0.1")
        예: Money(100000).apply_rate(Decimal("0.1")) → Money(10000)
        """
        return Money(self.amount * rate, self.currency)

    @property
    def is_positive(self) -> bool:
        """0보다 큰지. 배송비 무료 판정, 가격 검증 등에 사용."""
        return self.amount > 0

    def __eq__(self, other: object) -> bool:
        """같은 금액 + 같은 통화면 동일."""
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __gt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount >= other.amount

    def __hash__(self) -> int:
        """dict 키나 set 원소로 사용 가능하도록."""
        return hash((self.amount, self.currency))

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"