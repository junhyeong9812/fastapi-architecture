from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from app.tracking.application.query_handlers import GetOrderTrackingHandler
from app.tracking.application.queries import GetOrderTrackingQuery
from app.tracking.domain.exceptions import TrackingNotFoundError
from app.tracking.presentation.schemas import TrackingResponse, TrackingEventResponse

router = APIRouter(prefix="/api/v1/tracking", tags=["Tracking"],
                   route_class=DishkaRoute)


@router.get("/order/{order_id}")
async def get_tracking(
    order_id: str,
    handler: FromDishka[GetOrderTrackingHandler],
) -> TrackingResponse:
    """주문의 전체 추적 타임라인 조회."""
    try:
        tracking = await handler.handle(
            GetOrderTrackingQuery(order_id=order_id))
        return TrackingResponse(
            order_id=str(tracking.order_id),
            customer_name=tracking.customer_name,
            subscription_tier=tracking.subscription_tier,
            current_phase=tracking.current_phase.value,
            events=[
                TrackingEventResponse(
                    event_type=e.event_type, timestamp=e.timestamp,
                    module=e.module, detail=e.detail)
                for e in tracking.events
            ],
            started_at=tracking.started_at,
            completed_at=tracking.completed_at)
    except TrackingNotFoundError:
        raise HTTPException(404, "추적 정보가 없습니다")