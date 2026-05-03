from decimal import Decimal
from app.shared.value_objects import Money
from app.payments.domain.interfaces import DiscountResult


class NoDiscountPolicy:
    """미구독 고객용. 할인 0원."""
    def calculate_discount(self, amount: Money) -> DiscountResult:
        return DiscountResult(
            discount_amount=Money(Decimal("0"), amount.currency),
            discount_type="none",
        )


class SubscriptionDiscountPolicy:
    """구독 고객용. rate에 따라 할인.

    rate=0.10 → 10% 할인 (Premium)
    rate=0.05 → 5% 할인 (Basic)
    """
    def __init__(self, rate: Decimal, discount_type: str) -> None:
        self._rate = rate
        self._discount_type = discount_type

    def calculate_discount(self, amount: Money) -> DiscountResult:
        return DiscountResult(
            discount_amount=amount.apply_rate(self._rate),
            discount_type=self._discount_type,
        )