from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProcessPaymentCommand:
    """결제 처리 명령. OrderCreatedEvent 수신 시 자동 생성."""
    order_id: str
    amount: Decimal
    customer_name: str
    method: str     # "credit_card", "bank_transfer"