from typing import AsyncIterable

import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from dishka import make_async_container, Provider, Scope, provide, from_context

from app.shared.base_model import Base
from app.shared.event_bus import EventBus, InMemoryEventBus
from app.shared.subscription_context import SubscriptionContext
from app.shared.events import (
    OrderCreatedEvent, PaymentApprovedEvent, PaymentRejectedEvent,
    ShipmentCreatedEvent, ShipmentStatusChangedEvent,
)

# ORM 모델 import — 테이블 생성(create_all)에 필요
from app.orders.infrastructure.models import OrderModel, OrderItemModel  # noqa
from app.subscriptions.infrastructure.models import SubscriptionModel  # noqa
from app.payments.infrastructure.models import PaymentModel  # noqa
from app.shipping.infrastructure.models import ShipmentModel  # noqa

# Repository / Handler 클래스
from app.orders.infrastructure.repository import SQLAlchemyOrderRepository
from app.orders.application.command_handlers import (
    CreateOrderHandler, CancelOrderHandler,
)
from app.orders.application.query_handlers import (
    GetOrderHandler, ListOrdersHandler,
)
from app.subscriptions.infrastructure.repository import SQLAlchemySubscriptionRepository
from app.subscriptions.application.handlers import (
    CreateSubscriptionHandler, CancelSubscriptionHandler,
    GetSubscriptionHandler, GetActiveSubscriptionHandler,
)

# Phase 2: Payments
from app.payments.infrastructure.repository import SQLAlchemyPaymentRepository
from app.payments.infrastructure.fake_gateway import FakePaymentGateway
from app.payments.domain.policies import (
    NoDiscountPolicy, SubscriptionDiscountPolicy,
)
from app.payments.domain.interfaces import DiscountPolicy
from app.payments.application.command_handlers import ProcessPaymentHandler
from app.payments.application.event_handlers import (
    handle_order_created as payments_handle_order_created,
)
from app.orders.application.event_handlers import (
    handle_payment_approved as orders_handle_payment_approved,
    handle_payment_rejected as orders_handle_payment_rejected,
    handle_shipment_created as orders_handle_shipment_created,
    handle_shipment_delivered as orders_handle_shipment_delivered,
)
from app.payments.presentation.router import router as payments_router

# Phase 3: Shipping
from app.shipping.infrastructure.repository import SQLAlchemyShipmentRepository
from app.shipping.domain.policies import (
    StandardShippingFeePolicy, BasicShippingFeePolicy, PremiumShippingFeePolicy,
)
from app.shipping.domain.interfaces import ShippingFeePolicy
from app.shipping.application.command_handlers import UpdateShipmentStatusHandler
from app.shipping.application.event_handlers import (
    handle_payment_approved as shipping_handle_payment_approved,
)
from app.shipping.presentation.router import router as shipping_router

from app.tracking.infrastructure.models import OrderTrackingModel  # noqa
from app.tracking.infrastructure.repository import SQLAlchemyTrackingRepository
from app.tracking.application.query_handlers import GetOrderTrackingHandler
from app.tracking.application.event_handlers import (
    handle_order_created as tracking_handle_order_created,
    handle_payment_approved as tracking_handle_payment_approved,
    handle_payment_rejected as tracking_handle_payment_rejected,
    handle_shipment_created as tracking_handle_shipment_created,
    handle_shipment_status_changed as tracking_handle_shipment_status_changed,
)
from app.tracking.presentation.router import router as tracking_router


@pytest.fixture
async def async_engine():
    """SQLite 인메모리 엔진."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session_factory(async_engine):
    """테스트용 세션 팩토리."""
    return async_sessionmaker(
        async_engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False)


@pytest.fixture
async def event_bus():
    """테스트용 이벤트 버스. 테스트마다 새로 생성."""
    return InMemoryEventBus()


@pytest.fixture
async def async_client(session_factory, event_bus):
    """Dishka를 테스트용으로 오버라이드한 HTTP 클라이언트."""
    from fastapi import FastAPI
    from dishka.integrations.fastapi import setup_dishka
    from app.orders.presentation.router import router as orders_router
    from app.subscriptions.presentation.router import router as subs_router

    class TestProvider(Provider):
        """테스트 전용 DI Provider (Phase 1 + Phase 2)."""

        # dishka 1.x: FastAPI Request는 setup_dishka가 context로 주입 → from_context로 받음
        request = from_context(provides=Request, scope=Scope.REQUEST)

        @provide(scope=Scope.REQUEST)
        async def session(self) -> AsyncIterable[AsyncSession]:
            async with session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        @provide(scope=Scope.APP)
        def test_event_bus(self) -> EventBus:
            return event_bus

        # --- Orders ---
        @provide(scope=Scope.REQUEST)
        def order_repo(self, session: AsyncSession) -> SQLAlchemyOrderRepository:
            return SQLAlchemyOrderRepository(session)

        @provide(scope=Scope.REQUEST)
        def create_order(self, repo: SQLAlchemyOrderRepository,
                         eb: EventBus) -> CreateOrderHandler:
            return CreateOrderHandler(repo, eb)

        @provide(scope=Scope.REQUEST)
        def cancel_order(self, repo: SQLAlchemyOrderRepository,
                         eb: EventBus) -> CancelOrderHandler:
            return CancelOrderHandler(repo, eb)

        @provide(scope=Scope.REQUEST)
        def get_order(self, repo: SQLAlchemyOrderRepository) -> GetOrderHandler:
            return GetOrderHandler(repo)

        @provide(scope=Scope.REQUEST)
        def list_orders(self, repo: SQLAlchemyOrderRepository) -> ListOrdersHandler:
            return ListOrdersHandler(repo)

        # --- Subscriptions ---
        @provide(scope=Scope.REQUEST)
        def sub_repo(self, session: AsyncSession) -> SQLAlchemySubscriptionRepository:
            return SQLAlchemySubscriptionRepository(session)

        @provide(scope=Scope.REQUEST)
        def create_sub(self, repo: SQLAlchemySubscriptionRepository,
                       eb: EventBus) -> CreateSubscriptionHandler:
            return CreateSubscriptionHandler(repo, eb)

        @provide(scope=Scope.REQUEST)
        def cancel_sub(self, repo: SQLAlchemySubscriptionRepository,
                       eb: EventBus) -> CancelSubscriptionHandler:
            return CancelSubscriptionHandler(repo, eb)

        @provide(scope=Scope.REQUEST)
        def get_sub(self, repo: SQLAlchemySubscriptionRepository) -> GetSubscriptionHandler:
            return GetSubscriptionHandler(repo)

        @provide(scope=Scope.REQUEST)
        def get_active_sub(self, repo: SQLAlchemySubscriptionRepository) -> GetActiveSubscriptionHandler:
            return GetActiveSubscriptionHandler(repo)

        # --- Phase 2: SubscriptionContext + Payments ---
        @provide(scope=Scope.REQUEST)
        async def subscription_context(
            self,
            request: Request,
            repo: SQLAlchemySubscriptionRepository,
        ) -> SubscriptionContext:
            customer_name = request.headers.get("X-Customer-Name", "guest")
            sub = await repo.find_active_by_customer(customer_name)
            if sub is None or not sub.is_active():
                return SubscriptionContext.guest(customer_name)
            return SubscriptionContext(
                customer_name=customer_name,
                tier=sub.tier.value,
                is_active=True,
            )

        @provide(scope=Scope.REQUEST)
        def payment_repo(self, session: AsyncSession) -> SQLAlchemyPaymentRepository:
            return SQLAlchemyPaymentRepository(session)

        @provide(scope=Scope.REQUEST)
        def payment_gateway(self) -> FakePaymentGateway:
            return FakePaymentGateway()

        @provide(scope=Scope.REQUEST)
        def discount_policy(self, sub_ctx: SubscriptionContext) -> DiscountPolicy:
            match sub_ctx.tier:
                case "premium":
                    return SubscriptionDiscountPolicy(
                        rate=Decimal("0.10"), discount_type="premium_subscription")
                case "basic":
                    return SubscriptionDiscountPolicy(
                        rate=Decimal("0.05"), discount_type="basic_subscription")
                case _:
                    return NoDiscountPolicy()

        @provide(scope=Scope.REQUEST)
        def process_payment(
            self,
            repo: SQLAlchemyPaymentRepository,
            gateway: FakePaymentGateway,
            policy: DiscountPolicy,
            eb: EventBus,
        ) -> ProcessPaymentHandler:
            return ProcessPaymentHandler(repo, gateway, policy, eb)

        # --- Phase 3: Shipping ---
        @provide(scope=Scope.REQUEST)
        def shipment_repo(self, session: AsyncSession) -> SQLAlchemyShipmentRepository:
            return SQLAlchemyShipmentRepository(session)

        @provide(scope=Scope.REQUEST)
        def shipping_fee_policy(
            self, sub_ctx: SubscriptionContext,
        ) -> ShippingFeePolicy:
            match sub_ctx.tier:
                case "premium":
                    return PremiumShippingFeePolicy()
                case "basic":
                    return BasicShippingFeePolicy()
                case _:
                    return StandardShippingFeePolicy()

        @provide(scope=Scope.REQUEST)
        def update_status_handler(
            self,
            repo: SQLAlchemyShipmentRepository,
            eb: EventBus,
        ) -> UpdateShipmentStatusHandler:
            return UpdateShipmentStatusHandler(repo, eb)

        @provide(scope=Scope.REQUEST)
        def tracking_repo(
                self, session: AsyncSession,
        ) -> SQLAlchemyTrackingRepository:
            return SQLAlchemyTrackingRepository(session)

        @provide(scope=Scope.REQUEST)
        def get_tracking_handler(
                self, repo: SQLAlchemyTrackingRepository,
        ) -> GetOrderTrackingHandler:
            return GetOrderTrackingHandler(repo)

    # 테스트용 FastAPI 앱 생성
    test_app = FastAPI()
    test_app.include_router(orders_router)
    test_app.include_router(subs_router)
    test_app.include_router(payments_router)
    test_app.include_router(shipping_router)
    test_app.include_router(tracking_router)

    container = make_async_container(TestProvider())
    setup_dishka(container, test_app)

    # === Phase 2: 이벤트 핸들러 등록 ===
    async def on_order_created(event: OrderCreatedEvent) -> None:
        async with container() as rc:
            handler = await rc.get(ProcessPaymentHandler)
            await payments_handle_order_created(event, handler)

    async def on_payment_approved(event: PaymentApprovedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_payment_approved(event, repo)

    async def on_payment_rejected(event: PaymentRejectedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_payment_rejected(event, repo)

    # === Phase 3: Shipping 이벤트 핸들러 ===
    async def on_payment_approved_shipping(event: PaymentApprovedEvent) -> None:
        async with container() as rc:
            fee_policy = await rc.get(ShippingFeePolicy)
            repo = await rc.get(SQLAlchemyShipmentRepository)
            eb = await rc.get(EventBus)
            await shipping_handle_payment_approved(event, fee_policy, repo, eb)

    async def on_shipment_created(event: ShipmentCreatedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_shipment_created(event, repo)

    async def on_shipment_status_changed(event: ShipmentStatusChangedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyOrderRepository)
            await orders_handle_shipment_delivered(event, repo)

    async def on_order_created_tracking(event: OrderCreatedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyTrackingRepository)
            await tracking_handle_order_created(event, repo)

    async def on_payment_approved_tracking(event: PaymentApprovedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyTrackingRepository)
            await tracking_handle_payment_approved(event, repo)

    async def on_payment_rejected_tracking(event: PaymentRejectedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyTrackingRepository)
            await tracking_handle_payment_rejected(event, repo)

    async def on_shipment_created_tracking(event: ShipmentCreatedEvent) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyTrackingRepository)
            await tracking_handle_shipment_created(event, repo)

    async def on_shipment_status_changed_tracking(
            event: ShipmentStatusChangedEvent,
    ) -> None:
        async with container() as rc:
            repo = await rc.get(SQLAlchemyTrackingRepository)
            await tracking_handle_shipment_status_changed(event, repo)

    event_bus.subscribe(OrderCreatedEvent, on_order_created)
    event_bus.subscribe(PaymentApprovedEvent, on_payment_approved)
    event_bus.subscribe(PaymentApprovedEvent, on_payment_approved_shipping)
    event_bus.subscribe(PaymentRejectedEvent, on_payment_rejected)
    event_bus.subscribe(ShipmentCreatedEvent, on_shipment_created)
    event_bus.subscribe(ShipmentStatusChangedEvent, on_shipment_status_changed)
    event_bus.subscribe(OrderCreatedEvent, on_order_created_tracking)
    event_bus.subscribe(PaymentApprovedEvent, on_payment_approved_tracking)
    event_bus.subscribe(PaymentRejectedEvent, on_payment_rejected_tracking)
    event_bus.subscribe(ShipmentCreatedEvent, on_shipment_created_tracking)
    event_bus.subscribe(ShipmentStatusChangedEvent, on_shipment_status_changed_tracking)

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client

    await container.close()
