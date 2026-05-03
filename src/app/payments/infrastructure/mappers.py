from decimal import Decimal
from uuid import UUID
from app.shared.value_objects import Money
from app.payments.domain.entities import Payment, PaymentMethod, PaymentStatus
from app.payments.infrastructure.models import PaymentModel


def payment_to_model(p: Payment) -> PaymentModel:
    return PaymentModel(
        id=str(p.id), order_id=str(p.order_id),
        original_amount=float(p.original_amount.amount),
        discount_amount=float(p.discount_amount.amount),
        final_amount=float(p.final_amount.amount),
        currency=p.original_amount.currency,
        method=p.method.value, status=p.status.value,
        applied_discount_type=p.applied_discount_type,
        transaction_id=p.transaction_id,
        processed_at=p.processed_at)


def model_to_payment(m: PaymentModel) -> Payment:
    return Payment(
        id=UUID(m.id), order_id=UUID(m.order_id),
        original_amount=Money(Decimal(str(m.original_amount)), m.currency),
        discount_amount=Money(Decimal(str(m.discount_amount)), m.currency),
        final_amount=Money(Decimal(str(m.final_amount)), m.currency),
        method=PaymentMethod(m.method), status=PaymentStatus(m.status),
        applied_discount_type=m.applied_discount_type,
        transaction_id=m.transaction_id,
        processed_at=m.processed_at)