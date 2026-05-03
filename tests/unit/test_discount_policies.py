from decimal import Decimal
import pytest
from app.shared.value_objects import Money
from app.payments.domain.policies import (
    SubscriptionDiscountPolicy, NoDiscountPolicy,
)


class TestNoDiscount:
    """미구독 고객: 할인 없음."""

    def test_no_discount(self):
        policy = NoDiscountPolicy()
        result = policy.calculate_discount(Money(Decimal("100000")))
        assert result.discount_amount == Money(Decimal("0"))
        assert result.discount_type == "none"


class TestSubscriptionDiscount:
    """구독 고객: 등급별 할인."""

    def test_premium_10_percent(self):
        """Premium 구독: 10% 할인."""
        policy = SubscriptionDiscountPolicy(
            rate=Decimal("0.10"), discount_type="premium_subscription")
        result = policy.calculate_discount(Money(Decimal("100000")))
        assert result.discount_amount == Money(Decimal("10000"))    # 10만원의 10%
        assert result.discount_type == "premium_subscription"

    def test_basic_5_percent(self):
        """Basic 구독: 5% 할인."""
        policy = SubscriptionDiscountPolicy(
            rate=Decimal("0.05"), discount_type="basic_subscription")
        result = policy.calculate_discount(Money(Decimal("100000")))
        assert result.discount_amount == Money(Decimal("5000"))     # 10만원의 5%
        assert result.discount_type == "basic_subscription"