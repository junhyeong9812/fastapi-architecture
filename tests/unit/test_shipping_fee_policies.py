from decimal import Decimal
import pytest
from app.shared.value_objects import Money
from app.shipping.domain.policies import (
    StandardShippingFeePolicy,
    BasicShippingFeePolicy,
    PremiumShippingFeePolicy,
)


class TestStandardPolicy:
    """미구독 고객."""

    def test_under_50000(self):
        """5만원 미만 → 배송비 3,000원."""
        policy = StandardShippingFeePolicy()
        result = policy.calculate_fee(Money(Decimal("30000")))
        assert result.fee == Money(Decimal("3000"))
        assert result.discount_type == "none"

    def test_over_50000_free(self):
        """5만원 이상 → 무료배송."""
        policy = StandardShippingFeePolicy()
        result = policy.calculate_fee(Money(Decimal("50000")))
        assert result.fee == Money(Decimal("0"))


class TestBasicPolicy:
    """Basic 구독 고객."""

    def test_under_30000(self):
        """3만원 미만 → 1,500원 (기본 3,000원의 50%)."""
        policy = BasicShippingFeePolicy()
        result = policy.calculate_fee(Money(Decimal("20000")))
        assert result.fee == Money(Decimal("1500"))
        assert result.discount_type == "basic_half"

    def test_over_30000_free(self):
        """3만원 이상 → 무료배송."""
        policy = BasicShippingFeePolicy()
        result = policy.calculate_fee(Money(Decimal("30000")))
        assert result.fee == Money(Decimal("0"))


class TestPremiumPolicy:
    """Premium 구독 고객."""

    def test_any_amount_free(self):
        """금액 상관없이 항상 무료."""
        policy = PremiumShippingFeePolicy()
        result = policy.calculate_fee(Money(Decimal("1000")))
        assert result.fee == Money(Decimal("0"))
        assert result.discount_type == "premium_free"