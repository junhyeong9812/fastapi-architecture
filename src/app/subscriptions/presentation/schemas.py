from datetime import datetime
from pydantic import BaseModel


class CreateSubscriptionRequest(BaseModel):
    """구독 생성 요청."""
    customer_name: str
    tier: str


class SubscriptionResponse(BaseModel):
    id: str
    customer_name: str
    tier: str
    status: str
    is_active: bool
    started_at: datetime
    expires_at: datetime
