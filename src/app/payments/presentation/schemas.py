from datetime import datetime
from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    original_amount: float
    discount_amount: float
    final_amount: float
    applied_discount_type: str
    method: str
    status: str
    transaction_id: str | None
    processed_at: datetime | None