"""Command 처리 + 이벤트 발행.

★ 핵심 학습 포인트:
1. 핸들러는 Payments, Shipping을 import하지 않는다.
   이벤트를 publish할 뿐, 누가 수신하는지 모른다.
2. 핸들러는 Protocol(인터페이스)에 의존한다.
   SQLAlchemy를 직접 참조하지 않으므로 테스트에서 Fake로 교체 가능.
"""

from datetime import datetime, UTC
from uuid import UUID

from app.orders.domain.entities import Order, OrderItem
from app.shared.value_objects import Money
from app.orders.domain.interfaces import OrderRepositoryProtocol
from app.shared.event_bus import EventBus
from app.shared.events import OrderCreatedEvent, OrderCancelledEvent
from app.orders.application.commands import CreateOrderCommand, CancelOrderCommand

class CreateOrderHandler:
    """주문 생성 유즈케이스.

    Spring의 @Service 클래스와 비슷한 역할
    차이점: DI를 생성자 주입으로 받는다 (Dishika가 자동 주입
    """
    def __init__(self, repo: OrderRepositoryProtocol, event_bus: EventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def handle(self, command: CreateOrderCommand) -> UUID:
        # 1. Command의 DTO -> 도메인 객체로 변환
        items = [
            OrderItem(
                product_name=dto.product_name,
                quantity=dto.quantity,
                unit_price=Money(dto.unit_price),
            )
            for dto in command.items
        ]

        # 2. 도메인 엔티티 생성(검증은 Order.create()가 수행)
        order = Order.create(customer_name=command.customer_name, items=items)

        # 3. 결제 대기 상태로 전환 (생성 즉시)
        order.mark_payment_pending()

        # 4. DB 저장
        await self._repo.save(order)

        # 5. 이벤트 발행 -> 누가 수신하는지 모른다.
        # phase 2에서 Payments가 이 이벤트를 구동하여 자동 결제 시작
        await self._event_bus.publish(
            OrderCreatedEvent(
                order_id = order.id,
                customer_name = order.customer_name,
                total_amount=order.total_amount.amount,
                items_count=len(order.items),
                timestamp=datetime.now(UTC),
            )
        )
        return order.id

class CancelOrderHandler:
    """주문 취소 유즈케이스"""

    def __init__(self, repo: OrderRepositoryProtocol, event_bus: EventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def handle(self, command: CancelOrderCommand) -> None:
        # 1. 주문 조회
        order = await self._repo.find_by_id(UUID(command.order_id))
        if order is None:
            from app.orders.domain.exceptions import OrderNotFoundError
            raise OrderNotFoundError(command.order_id)

        # 2. 취소 (상태 전이 검증은 엔티티가 수행)
        # PAID 이후 취소 시도 -> InvalidStatusTransition 예외 발생
        order.cancel()

        # 3. DB 업데이트
        await self._repo.update(order)

        # 4. 이벤트 발행
        await self._event_bus.publish(
            OrderCancelledEvent(
                order_id=order.id,
                reason="고객 요청",
                timestamp=datetime.now(UTC),
            )
        )