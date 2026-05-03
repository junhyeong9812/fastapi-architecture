"""Payments API. 결제 생성은 이벤트가 처리하므로 읽기 전용 API만 있다."""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from app.payments.infrastructure.repository import SQLAlchemyPaymentRepository
from app.payments.presentation.schemas import PaymentResponse

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"],
                   route_class=DishkaRoute)


def _payment_to_response(p) -> PaymentResponse:
    return PaymentResponse(
        id=str(p.id), order_id=str(p.order_id),
        original_amount=float(p.original_amount.amount),
        discount_amount=float(p.discount_amount.amount),
        final_amount=float(p.final_amount.amount),
        applied_discount_type=p.applied_discount_type,
        method=p.method.value, status=p.status.value,
        transaction_id=p.transaction_id,
        processed_at=p.processed_at)


@router.get("/order/{order_id}")
async def get_payment_by_order(
    order_id: str,
    repo: FromDishka[SQLAlchemyPaymentRepository],
) -> PaymentResponse | None:
    """주문별 결제 조회. GET /api/v1/payments/order/{order_id}"""
    payment = await repo.find_by_order_id(UUID(order_id))
    if payment is None:
        raise HTTPException(404, "결제 내역이 없습니다")
    return _payment_to_response(payment)