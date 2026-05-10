from datetime import datetime
from pydantic import BaseModel


class TrackingEventResponse(BaseModel):
    event_type: str
    timestamp: datetime
    module: str
    detail: dict


class TrackingResponse(BaseModel):
    order_id: str
    customer_name: str
    subscription_tier: str
    current_phase: str
    events: list[TrackingEventResponse]
    started_at: datetime
    completed_at: datetime | None