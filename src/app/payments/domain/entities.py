from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from app.shared.value_objects import Money


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    VIRTUAL_ACCOUNT = "virtual_account"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentError(Exception):
    pass


@dataclass
class Payment:
    id: UUID
    order_id: UUID
    original_amount: Money      # 할인 전 금액
    discount_amount: Money      # 할인 금액
    final_amount: Money         # 실제 결제 금액 = original - discount
    method: PaymentMethod
    status: PaymentStatus
    applied_discount_type: str  # "none", "basic_subscription", "premium_subscription"
    transaction_id: str | None  # PG 승인번호
    processed_at: datetime | None

    @classmethod
    def create(
        cls, order_id: UUID, original_amount: Money,
        discount_amount: Money, final_amount: Money,
        method: PaymentMethod, applied_discount_type: str,
    ) -> "Payment":
        return cls(
            id=uuid4(), order_id=order_id,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            method=method,
            status=PaymentStatus.PENDING,   # 생성 시 PENDING
            applied_discount_type=applied_discount_type,
            transaction_id=None,
            processed_at=None,
        )

    def approve(self, transaction_id: str) -> None:
        """PG 승인 → APPROVED."""
        if self.status != PaymentStatus.PENDING:
            raise PaymentError(f"PENDING이 아닌 결제는 승인 불가: {self.status}")
        self.status = PaymentStatus.APPROVED
        self.transaction_id = transaction_id
        self.processed_at = datetime.now(UTC)

    def reject(self, reason: str) -> None:
        """PG 거절 → REJECTED."""
        if self.status != PaymentStatus.PENDING:
            raise PaymentError(f"PENDING이 아닌 결제는 거절 불가: {self.status}")
        self.status = PaymentStatus.REJECTED
        self.processed_at = datetime.now(UTC)