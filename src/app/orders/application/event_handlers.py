"""외부 이벤트 수신 핸들러.

Phase 1에서는 빈 파일. 자리만 마련해둔다.
Phase 2에서 PaymentApprovedEvent → order.mark_paid() 추가.
Phase 3에서 ShipmentCreatedEvent → order.mark_shipping() 추가.
"""
from uuid import UUID
from app.orders.domain.interfaces import OrderRepositoryProtocol
from app.shared.events import PaymentApprovedEvent, PaymentRejectedEvent


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
