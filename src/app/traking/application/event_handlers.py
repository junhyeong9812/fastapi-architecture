"""★ 모든 도메인 이벤트를 구독하여 타임라인에 기록.

Tracking은 읽기+기록 전용. 다른 모듈에 이벤트를 발행하지 않는다.
모든 모듈의 이벤트를 구독하지만, 어떤 모듈도 직접 import하지 않는다.
(shared/events.py만 참조)
"""

from app.tracking.domain.entities import OrderTracking, TrackingPhase
from app.tracking.domain.interfaces import TrackingRepositoryProtocol
from app.shared.events import (
    OrderCreatedEvent, PaymentApprovedEvent, PaymentRejectedEvent,
    ShipmentCreatedEvent, ShipmentStatusChangedEvent,
)


async def handle_order_created(
    event: OrderCreatedEvent, repo: TrackingRepositoryProtocol,
) -> None:
    """주문 생성 → 추적 시작."""
    tracking = OrderTracking.create(
        order_id=event.order_id,
        customer_name=event.customer_name,
        subscription_tier="unknown",
    )
    tracking.add_event("order.created", "orders", {
        "amount": str(event.total_amount),
        "items_count": event.items_count,
    })
    tracking.current_phase = TrackingPhase.PAYMENT_PROCESSING
    await repo.save(tracking)


async def handle_payment_approved(
    event: PaymentApprovedEvent, repo: TrackingRepositoryProtocol,
) -> None:
    """결제 승인 기록."""
    tracking = await repo.find_by_order_id(event.order_id)
    if tracking:
        tracking.add_event("payment.approved", "payments", {
            "final_amount": str(event.final_amount),
            "discount_type": event.applied_discount_type,
        })
        tracking.current_phase = TrackingPhase.PAYMENT_COMPLETED
        await repo.update(tracking)


async def handle_payment_rejected(
    event: PaymentRejectedEvent, repo: TrackingRepositoryProtocol,
) -> None:
    """결제 거절 → 추적 실패 처리."""
    tracking = await repo.find_by_order_id(event.order_id)
    if tracking:
        tracking.add_event("payment.rejected", "payments", {
            "reason": event.reason,
        })
        tracking.mark_failed(event.reason)
        await repo.update(tracking)


async def handle_shipment_created(
    event: ShipmentCreatedEvent, repo: TrackingRepositoryProtocol,
) -> None:
    """배송 생성 기록."""
    tracking = await repo.find_by_order_id(event.order_id)
    if tracking:
        tracking.add_event("shipment.created", "shipping", {
            "shipping_fee": str(event.shipping_fee),
            "discount_type": event.fee_discount_type,
        })
        tracking.current_phase = TrackingPhase.SHIPPING
        await repo.update(tracking)


async def handle_shipment_status_changed(
    event: ShipmentStatusChangedEvent, repo: TrackingRepositoryProtocol,
) -> None:
    """배송 상태 변경 기록. delivered면 추적 완료."""
    tracking = await repo.find_by_order_id(event.order_id)
    if tracking:
        tracking.add_event(f"shipment.{event.new_status}", "shipping", {})
        if event.new_status == "delivered":
            tracking.mark_completed()
        await repo.update(tracking)