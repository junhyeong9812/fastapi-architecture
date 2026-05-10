"""외부 이벤트 수신 핸들러.

Phase 1에서는 빈 파일. 자리만 마련해둔다.
Phase 2에서 PaymentApprovedEvent → order.mark_paid() 추가.
Phase 3에서 ShipmentCreatedEvent → order.mark_shipping() 추가.
"""
from uuid import UUID
from app.orders.domain.interfaces import OrderRepositoryProtocol
from app.shared.events import PaymentApprovedEvent, PaymentRejectedEvent, ShipmentCreatedEvent, ShipmentStatusChangedEvent


async def handle_payment_approved(
    event: PaymentApprovedEvent, repo: OrderRepositoryProtocol
) -> None:
    """결제 승인 → 주문 상태를 PAID로 변경."""
    order = await repo.find_by_id(event.order_id)
    if order:
        order.mark_paid()
        await repo.update(order)


async def handle_payment_rejected(
    event: PaymentRejectedEvent, repo: OrderRepositoryProtocol
) -> None:
    """결제 거절 → 주문 자동 취소."""
    order = await repo.find_by_id(event.order_id)
    if order:
        order.cancel()
        await repo.update(order)

async def handle_shipment_created(
    event: ShipmentCreatedEvent, repo: OrderRepositoryProtocol,
) -> None:
    """배송 생성됨 → 주문을 SHIPPING으로 전이.

    ★ Orders는 Shipping을 import하지 않는다.
    event 페이로드(order_id)만으로 처리.
    """
    order = await repo.find_by_id(event.order_id)
    if order:
        order.mark_shipping()
        await repo.update(order)


async def handle_shipment_delivered(
    event: ShipmentStatusChangedEvent, repo: OrderRepositoryProtocol,
) -> None:
    """배송 상태가 delivered면 → 주문을 DELIVERED로 전이.

    in_transit으로의 변경은 Orders 입장에서 SHIPPING 유지이므로 처리하지 않는다.
    """
    if event.new_status == "delivered":
        order = await repo.find_by_id(event.order_id)
        if order:
            order.mark_delivered()
            await repo.update(order)