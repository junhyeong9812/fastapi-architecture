"""Money 값 객체 테스트.

★ 이 테스트를 먼저 작성하고 실행하면 ImportError가 난다.
그 다음에 value_objects.py를 구현하면 테스트가 통과한다.
이것이 TDD의 흐름: Red(실패) → Green(통과) → Refactor(정리)
"""

from decimal import Decimal
import pytest
from app.orders.domain.value_objects import Money

class TestMoneyCreation:
    """Money 생성 테스트."""

    def test_create_money(self):
        """정상적인 Money 생성."""
        money = Money(Decimal("10000"), "KRW")
        assert money.amount == Decimal("10000")
        assert money.currency == "KRW"

    def test_default_currency_is_krw(self):
        """통화를 지정하지 않으면 기본값 KRW."""
        money = Money(Decimal("5000"))
        assert money.currency == "KRW"

    def test_negative_amount_raises(self):
        """음수 금액은 생성 불가. Money는 항상 0 이상."""
        with pytest.raises(ValueError, match="음수"):
            Money(Decimal("-100"))

class TestMoneyArithmetic:
    """money 사칙연산 테스트. 모든 연산은 새 인스턴스를 반환(불변)."""

    def test_add(self):
        a = Money(Decimal("10000"))
        b = Money(Decimal("5000"))
        result = a.add(b)
        assert result.amount == Decimal("15000")

    def test_add_different_currency_raises(self):
        """다른 통화끼리 더하기 불가."""
        krw = Money(Decimal("10000"), "KRW")
        usd = Money(Decimal("10"), "USD")
        with pytest.raises(ValueError, match="통화"):
            krw.add(usd)

    def test_subtract(self):
        a = Money(Decimal("10000"))
        b = Money(Decimal("3000"))
        result = a.subtract(b)
        assert result.amount == Decimal("7000")

    def test_multiply(self):
        """수량 곱하기. 키보드 5000원 x 3개 = 15000원."""
        money = Money(Decimal("5000"))
        result = money.multiply(3)
        assert result.amount == Decimal("15000")

    def test_apply_rate(self):
        """비율 적용. 10000원의 10% = 1000원 (할인 계산에 사용)."""
        money = Money(Decimal("10000"))
        result = money.apply_rate(Decimal("0.1"))
        assert result.amount == Decimal("1000")

class TestMoneyComparison:
    """ Money 비교 연산 테스트. """

    def test_equal(self):
        a = Money(Decimal("10000"))
        b = Money(Decimal("10000"))
        assert a == b

    def test_not_equal(self):
        a = Money(Decimal("10000"))
        b = Money(Decimal("5000"))
        assert a != b

    def test_greater_than(self):
        a = Money(Decimal("10000"))
        b = Money(Decimal("5000"))
        assert a > b

    def test_is_positive(self):
        """0원은 positive가 아님. 배송비 무료 판정 등에 사용."""
        assert Money(Decimal("100")).is_positive is True
        assert Money(Decimal("0")).is_positive is False

