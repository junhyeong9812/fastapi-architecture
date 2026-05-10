"""배송비 정책 구현체.

★ Payments의 할인 정책과 동일한 패턴.
Shipping은 Subscriptions를 모른다. DI가 적절한 정책을 주입한다.
"""

from decimal import Decimal
from app.shared.value_objects import Money
from app.shipping.domain.interfaces import ShippingFeeResult

BASE_FEE = Money(Decimal("3000"))       # 기본 배송비 3,000원
ZERO = Money(Decimal("0"))


class StandardShippingFeePolicy:
    """미구독: 기본 3,000원, 5만원↑ 무료."""

    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        if order_amount >= Money(Decimal("50000")):
            return ShippingFeeResult(
                fee=ZERO, original_fee=BASE_FEE,
                discount_type="none", reason="5만원 이상 무료배송")
        return ShippingFeeResult(
            fee=BASE_FEE, original_fee=BASE_FEE,
            discount_type="none", reason="기본 배송비")


class BasicShippingFeePolicy:
    """Basic 구독: 50% 할인 → 1,500원, 3만원↑ 무료."""

    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        if order_amount >= Money(Decimal("30000")):
            return ShippingFeeResult(
                fee=ZERO, original_fee=BASE_FEE,
                discount_type="basic_half", reason="Basic 구독 3만원↑ 무료")
        return ShippingFeeResult(
            fee=Money(Decimal("1500")), original_fee=BASE_FEE,
            discount_type="basic_half", reason="Basic 구독 50% 할인")


class PremiumShippingFeePolicy:
    """Premium 구독: 항상 무료."""

    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        return ShippingFeeResult(
            fee=ZERO, original_fee=BASE_FEE,
            discount_type="premium_free", reason="Premium 구독 무료배송")