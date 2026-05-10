import json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tracking.domain.entities import OrderTracking
from app.tracking.infrastructure.models import OrderTrackingModel
from app.tracking.infrastructure.mappers import tracking_to_model, model_to_tracking


class SQLAlchemyTrackingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, tracking: OrderTracking) -> None:
        self._session.add(tracking_to_model(tracking))
        await self._session.flush()

    async def find_by_order_id(self, order_id: UUID) -> OrderTracking | None:
        stmt = select(OrderTrackingModel).where(
            OrderTrackingModel.order_id == str(order_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_tracking(model) if model else None

    async def update(self, tracking: OrderTracking) -> None:
        model = await self._session.get(OrderTrackingModel, str(tracking.id))
        if model is None:
            return
        model.current_phase = tracking.current_phase.value
        events_data = [
            {"event_type": e.event_type, "timestamp": e.timestamp.isoformat(),
             "module": e.module, "detail": e.detail}
            for e in tracking.events
        ]
        model.events_json = json.dumps(events_data, ensure_ascii=False)
        model.completed_at = tracking.completed_at
        await self._session.flush()