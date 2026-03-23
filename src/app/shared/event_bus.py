"""인메모리 이벤트 버스.

★ 학습 포인트 (이벤트 기반 통신):

문제: Orders가 주문을 생성하면 Payments가 자동으로 결제를 시작해야 한다.
     Orders가 Payments를 직접 호출하면 모듈 간 결합이 생긴다.

해결: 이벤트 버스를 통한 간접 통신
  - Orders가 OrderCreatedEvent를 publish (발행)
  - Payments가 그 이벤트를 subscribe (구독)하여 자동으로 결제 시작
  - Orders는 Payments를 모르고, Payments는 Orders를 모른다

Protocol로 정의하여 나중에 Redis Pub/Sub이나 Kafka로 교체 가능.
지금은 InMemoryEventBus로 같은 프로세스 안에서 동작.
"""

from collections import defaultdict
from typing import Callable, Protocol

import structlog

logger = structlog.get_logger()


class EventBus(Protocol):
    """이벤트 버스 인터페이스.

    도메인 코드와 핸들러는 이 Protocol만 의존한다.
    InMemoryEventBus인지, RedisEventBus인지 모른다.
    Spring의 ApplicationEventPublisher와 비슷한 역할.
    """
    async def publish(self, event: object) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...


class InMemoryEventBus:
    """메모리 기반 구현체.

    단일 프로세스에서 동작하며, 학습용으로 충분하다.
    _handlers는 {이벤트 타입: [핸들러 함수 목록]} 형태의 딕셔너리.
    """

    def __init__(self) -> None:
        # defaultdict: 처음 보는 키도 자동으로 빈 리스트 생성
        # 예: self._handlers[OrderCreatedEvent] → 자동으로 [] 생성
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """특정 이벤트 타입에 핸들러를 등록한다.

        예: event_bus.subscribe(OrderCreatedEvent, handle_order_created)
        → OrderCreatedEvent가 발행되면 handle_order_created가 호출됨
        """
        self._handlers[event_type].append(handler)
        logger.info(
            "event_subscribed",
            event_name=event_type.__name__,       # "OrderCreatedEvent"
            handler_name=handler.__qualname__,     # "handle_order_created"
        )

    async def publish(self, event: object) -> None:
        """이벤트를 발행하면, 등록된 모든 핸들러가 순차 호출된다.

        하나의 이벤트에 여러 핸들러가 등록될 수 있다.
        예: PaymentApprovedEvent → [orders_handler, shipping_handler, tracking_handler]
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        logger.info(
            "event_published",
            event_name=event_type.__name__,
            handler_count=len(handlers),
        )
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # ★ 핵심: 하나의 핸들러가 실패해도 다른 핸들러는 계속 실행
                # 결제 핸들러가 실패해도 Tracking 핸들러는 동작해야 함
                logger.error(
                    "event_handler_failed",
                    event_name=event_type.__name__,
                    handler_name=handler.__qualname__,
                    error=str(e),
                )