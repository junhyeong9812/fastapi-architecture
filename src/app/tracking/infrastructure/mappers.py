import json
from datetime import datetime
from uuid import UUID
from app.tracking.domain.entities import (
    OrderTracking, TrackingPhase, TrackingEvent,
)
from app.tracking.infrastructure.models import OrderTrackingModel


def tracking_to_model(t: OrderTracking) -> OrderTrackingModel:
    events_data = [
        {"event_type": e.event_type, "timestamp": e.timestamp.isoformat(),
         "module": e.module, "detail": e.detail}
        for e in t.events
    ]
    return OrderTrackingModel(
        id=str(t.id), order_id=str(t.order_id),
        customer_name=t.customer_name,
        subscription_tier=t.subscription_tier,
        current_phase=t.current_phase.value,
        events_json=json.dumps(events_data, ensure_ascii=False),
        started_at=t.started_at, completed_at=t.completed_at)


def model_to_tracking(m: OrderTrackingModel) -> OrderTracking:
    events_data = json.loads(m.events_json)
    events = [
        TrackingEvent(
            event_type=e["event_type"],
            timestamp=datetime.fromisoformat(e["timestamp"]),
            module=e["module"], detail=e["detail"])
        for e in events_data
    ]
    return OrderTracking(
        id=UUID(m.id), order_id=UUID(m.order_id),
        customer_name=m.customer_name,
        subscription_tier=m.subscription_tier,
        events=events, current_phase=TrackingPhase(m.current_phase),
        started_at=m.started_at, completed_at=m.completed_at)