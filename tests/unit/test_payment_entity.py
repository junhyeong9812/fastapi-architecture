from decimal import Decimal
from uuid import uuid4
import pytest
from app.shared.value_objects import Money
from app.payments.domain.entities import Payment, PaymentMethod, PaymentStatus


class TestPaymentCreation:
    def test_create_payment(self):
        """결제 생성 → PENDING 상태."""
        payment = Payment.create(
            order_id=uuid4(),
            original_amount=Money(Decimal("100000")),
            discount_amount=Money(Decimal("10000")),
            final_amount=Money(Decimal("90000")),
            method=PaymentMethod.CREDIT_CARD,
            applied_discount_type="premium_subscription",
        )
        assert payment.status == PaymentStatus.PENDING
        assert payment.final_amount == Money(Decimal("90000"))


class TestPaymentStatusTransition:
    def _make_payment(self) -> Payment:
        return Payment.create(
            order_id=uuid4(),
            original_amount=Money(Decimal("100000")),
            discount_amount=Money(Decimal("0")),
            final_amount=Money(Decimal("100000")),
            method=PaymentMethod.CREDIT_CARD,
            applied_discount_type="none",
        )

    def test_approve(self):
        """PENDING → APPROVED."""
        payment = self._make_payment()
        payment.approve("txn_12345")
        assert payment.status == PaymentStatus.APPROVED

    def test_reject(self):
        """PENDING → REJECTED."""
        payment = self._make_payment()
        payment.reject("잔액 부족")
        assert payment.status == PaymentStatus.REJECTED

    def test_approve_already_approved_raises(self):
        """이미 승인된 결제는 다시 승인 불가."""
        payment = self._make_payment()
        payment.approve("txn_12345")
        with pytest.raises(Exception):
            payment.approve("txn_67890")