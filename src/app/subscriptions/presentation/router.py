from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from app.subscriptions.domain.entities import (
    Subscription, SubscriptionNotFoundError, InvalidSubscriptionError,
)
from app.subscriptions.application.handlers import (
    CreateSubscriptionCommand, CancelSubscriptionCommand,
    GetSubscriptionQuery, GetActiveSubscriptionQuery,
    CreateSubscriptionHandler, CancelSubscriptionHandler,
    GetSubscriptionHandler, GetActiveSubscriptionHandler,
)
from app.subscriptions.presentation.schemas import (
    CreateSubscriptionRequest, SubscriptionResponse,
)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"],route_class=DishkaRoute)

def _sub_to_response(sub: Subscription) -> SubscriptionResponse:
    """도메인 엔티티 -> HTTP 응답 변환."""
    return SubscriptionResponse(
        id=str(sub.id),
        customer_name=sub.customer_name,
        tier=sub.tier.value,
        status=sub.status.value,
        is_active=sub.is_active(),
        started_at=sub.started_at,
        expires_at=sub.expires_at,
    )

@router.post("/", status_code=201)
async def create_subscription(
        body: CreateSubscriptionRequest,
        handler: FromDishka[CreateSubscriptionHandler],
)-> SubscriptionResponse:
    """구독 생성. POST /api/v1/subscriptions"""
    try:
        sub_id = await handler.handle(
            CreateSubscriptionCommand(customer_name=body.customer_name, tier=body.tier))
        sub = await handler._repo.find_by_id(sub_id)
        return _sub_to_response(sub)
    except InvalidSubscriptionError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{subscription_id}")
async def get_subscription(
        subscription_id: str,
        handler: FromDishka[GetSubscriptionHandler],
) -> SubscriptionResponse:
    """구독 상세 조회. GET /api/v1/subscriptions"""
    try:
        sub = await handler.handle(
            GetSubscriptionQuery(subscription_id=subscription_id)
        )
        return _sub_to_response(sub)
    except SubscriptionNotFoundError:
        raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다.")

@router.get("/customer/{customer_name}")
async def get_active_subscription(
        customer_name: str,
        handler: FromDishka[GetActiveSubscriptionHandler],
) -> SubscriptionResponse | None:
    """고객의 활성 구독 조회. 없으면 null 반환.
    GET /api/v1/subscriptions/customer/홍길동
    """
    sub = await handler.handle(
        GetActiveSubscriptionQuery(customer_name=customer_name)
    )
    if sub is None:
        return None
    return _sub_to_response(sub)

@router.post("/{subscription_id}/cancel")
async def cancel_subscription(
        subscription_id: str,
        handler: FromDishka[CancelSubscriptionHandler],
        get_handler: FromDishka[GetSubscriptionHandler],
) -> SubscriptionResponse:
    """구독 최소. POST /api/v1/subscriptions/{id}/cancel"""
    try:
        await handler.handle(
            CancelSubscriptionCommand(subscription_id=subscription_id)
        )
        sub = await get_handler.handle(
            GetSubscriptionQuery(subscription_id=subscription_id)
        )
        return _sub_to_response(sub)
    except SubscriptionNotFoundError:
        raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")
    except InvalidSubscriptionError as e:
        raise HTTPException(status_code=400, detail=str(e))