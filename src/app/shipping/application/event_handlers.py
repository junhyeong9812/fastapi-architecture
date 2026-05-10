"""PaymentApprovedEvent → 배송 자동 생성.

★ Payments를 import하지 않는다. event 데이터만 사용.
"""

from app.shared.events import PaymentApprovedEvent
from app.shared.value_objects import Money
from app.shipping.domain.entities import Shipment, Address
from app.shipping.domain.interfaces import ShippingFeePolicy, ShipmentRepositoryProtocol
from app.shared.event_bus import EventBus
from app.shared.events import ShipmentCreatedEvent
from datetime import datetime, UTC


async def handle_payment_approved(
    event: PaymentApprovedEvent,
    fee_policy: ShippingFeePolicy,
    repo: ShipmentRepositoryProtocol,
    event_bus: EventBus,
) -> None:
    order_amount = Money(event.final_amount)
    fee_result = fee_policy.calculate_fee(order_amount)

    shipment = Shipment.create(
        order_id=event.order_id,
        address=Address(street="기본 주소", city="서울", zip_code="00000"),
        shipping_fee=fee_result.fee,
        original_fee=fee_result.original_fee,
        fee_discount_type=fee_result.discount_type,
    )
    await repo.save(shipment)

    await event_bus.publish(
        ShipmentCreatedEvent(
            shipment_id=shipment.id, order_id=shipment.order_id,
            shipping_fee=shipment.shipping_fee.amount,
            fee_discount_type=shipment.fee_discount_type,
            tracking_number=None, timestamp=datetime.now(UTC),
        )
    )