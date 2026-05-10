from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka

from app.shared.di_container import create_container
from app.shared.middleware import LoggingMiddleware
from app.shared.event_bus import EventBus
from app.shared.events import (
    OrderCreatedEvent, PaymentApprovedEvent, PaymentRejectedEvent,
    ShipmentCreatedEvent, ShipmentStatusChangedEvent,
)

from app.orders.infrastructure.repository import SQLAlchemyOrderRepository
from app.payments.application.command_handlers import ProcessPaymentHandler

from app.payments.application.event_handlers import (
    handle_order_created as payments_handle_order_created,
)

from app.shipping.infrastructure.repository import SQLAlchemyShipmentRepository
from app.shipping.application.event_handlers import (
    handle_payment_approved as shipping_handle_payment_approved,
)
from app.shipping.domain.interfaces import ShippingFeePolicy
from app.orders.application.event_handlers import (
    handle_payment_approved as orders_handle_payment_approved,
    handle_payment_rejected as orders_handle_payment_rejected,
    handle_shipment_created as orders_handle_shipment_created,
    handle_shipment_delivered as orders_handle_shipment_delivered,
)

from app.orders.presentation.router import router as orders_router
from app.subscriptions.presentation.router import router as subscriptions_router
from app.payments.presentation.router import router as payments_router
from app.shipping.presentation.router import router as shipping_router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

def register_event_handlers(event_bus: EventBus, container) -> None:

    async def on_order_created(event: OrderCreatedEvent) -> None:
        # HTTP 요청 바깥에서 실행되므로 REQUEST 스코프를 수동으로 연다
        async with container() as request_container:
            handler = await request_container.get(ProcessPaymentHandler)
            await payments_handle_order_created(event, handler)

    async def on_payment_approved(event: PaymentApprovedEvent) -> None:
        async with container() as request_container:
            repo = await request_container.get(SQLAlchemyOrderRepository)
            await orders_handle_payment_approved(event, repo)

    async def on_payment_rejected(event: PaymentRejectedEvent) -> None:
        async with container() as request_container:
            repo = await request_container.get(SQLAlchemyOrderRepository)
            await orders_handle_payment_rejected(event, repo)

    # === Phase 3 신규: PaymentApproved → Shipping (배송 자동 생성) ===
    async def on_payment_approved_shipping(event: PaymentApprovedEvent) -> None:
        async with container() as rc:
            fee_policy = await rc.get(ShippingFeePolicy)
            repo = await rc.get(SQLAlchemyShipmentRepository)
            eb = await rc.get(EventBus)
            await shipping_handle_payment_approved(event, fee_policy, repo, eb)

    # === Phase 3 신규: ShipmentCreated → Orders (SHIPPING 전이) ===
    async def on_shipment_created(event: ShipmentCreatedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_shipment_created(event, repo)

    # === Phase 3 신규: ShipmentStatusChanged → Orders (DELIVERED 전이) ===
    async def on_shipment_status_changed(event: ShipmentStatusChangedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_shipment_delivered(event, repo)

    # 등록
    event_bus.subscribe(OrderCreatedEvent, on_order_created)
    event_bus.subscribe(PaymentApprovedEvent, on_payment_approved)
    event_bus.subscribe(PaymentApprovedEvent, on_payment_approved_shipping)  # ★ 동일 이벤트에 핸들러 누적
    event_bus.subscribe(PaymentRejectedEvent, on_payment_rejected)
    event_bus.subscribe(ShipmentCreatedEvent, on_shipment_created)
    event_bus.subscribe(ShipmentStatusChangedEvent, on_shipment_status_changed)

@asynccontextmanager
async def lifespan(app: FastAPI):
    container = app.state.dishka_container
    # APP 스코프의 EventBus를 가져와 핸들러 등록
    event_bus = await container.get(EventBus)
    register_event_handlers(event_bus, container)
    yield
    await app.state.dishka_container.close()

# FastAPI 앱 생성
app = FastAPI(
    title="ShopTracker",
    version="0.1.0",
    lifespan=lifespan,
)

# 미들웨어 등록 — 모든 요청에 로깅 적용
app.add_middleware(LoggingMiddleware)

# DI 컨테이너 생성 + FastAPI에 연결
container = create_container()
setup_dishka(container, app)

# 라우터 등록 — 각 모듈의 API 엔드포인트
app.include_router(orders_router)
app.include_router(subscriptions_router)
app.include_router(payments_router)
app.include_router(shipping_router)

@app.get("/health")
async def health():
    """헬스 체크. 서버가 살아있는지 확인용."""
    return {"status": "ok"}