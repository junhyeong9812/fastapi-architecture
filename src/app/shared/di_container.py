from dishka import Provider, Scope, make_async_container, provide, AsyncContainer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from decimal import Decimal
from fastapi import Request

from app.shared.subscription_context import SubscriptionContext
from app.shared.config import AppConfig, get_config
from app.shared.database import create_engine, create_session_factory
from app.shared.event_bus import EventBus, InMemoryEventBus

# Orders — infrastructure 구현체를 여기서만 import
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
from app.payments.infrastructure.repository import SQLAlchemyPaymentRepository
from app.payments.infrastructure.fake_gateway import FakePaymentGateway
from app.payments.domain.policies import (
    NoDiscountPolicy, SubscriptionDiscountPolicy,
)
from app.payments.domain.interfaces import DiscountPolicy
from app.payments.application.command_handlers import ProcessPaymentHandler

from app.shipping.infrastructure.repository import SQLAlchemyShipmentRepository
from app.shipping.domain.policies import (
    StandardShippingFeePolicy,
    BasicShippingFeePolicy,
    PremiumShippingFeePolicy,
)
from app.shipping.domain.interfaces import ShippingFeePolicy
from app.shipping.application.command_handlers import UpdateShipmentStatusHandler

class AppProvider(Provider):

    @provide(scope=Scope.APP)
    def config(self) -> AppConfig:
        return get_config()

    @provide(scope=Scope.APP)
    def engine(self, config: AppConfig) -> AsyncEngine:
        return create_engine(config)

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    @provide(scope=Scope.APP)
    def event_bus(self) -> EventBus:
        return InMemoryEventBus()

    @provide(scope=Scope.REQUEST)
    async def session(
            self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncSession:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise

class OrdersProvider(Provider):

    @provide(scope=Scope.REQUEST)
    def order_repository(self, session: AsyncSession) -> SQLAlchemyOrderRepository:
        return SQLAlchemyOrderRepository(session)

    @provide(scope=Scope.REQUEST)
    def create_order_handler(
            self, repo: SQLAlchemyOrderRepository, event_bus: EventBus
    ) -> CreateOrderHandler:
        return CreateOrderHandler(repo, event_bus)

    @provide(scope=Scope.REQUEST)
    def cancel_order_handler(
            self, repo: SQLAlchemyOrderRepository, event_bus: EventBus
    ) -> CancelOrderHandler:
        return CancelOrderHandler(repo, event_bus)

    @provide(scope=Scope.REQUEST)
    def get_order_handler(
            self, repo: SQLAlchemyOrderRepository
    ) -> GetOrderHandler:
        return GetOrderHandler(repo)

    @provide(scope=Scope.REQUEST)
    def list_orders_handler(
            self, repo: SQLAlchemyOrderRepository
    ) -> ListOrdersHandler:
        return ListOrdersHandler(repo)

class SubscriptionsProvider(Provider):

    @provide(scope=Scope.REQUEST)
    def subscription_repository(
            self, session: AsyncSession
    ) -> SQLAlchemySubscriptionRepository:
        return SQLAlchemySubscriptionRepository(session)

    @provide(scope=Scope.REQUEST)
    def create_subscription_handler(
            self, repo: SQLAlchemySubscriptionRepository, event_bus: EventBus
    ) -> CreateSubscriptionHandler:
        return CreateSubscriptionHandler(repo, event_bus)

    @provide(scope=Scope.REQUEST)
    def cancel_subscription_handler(
            self, repo: SQLAlchemySubscriptionRepository, event_bus: EventBus
    ) -> CancelSubscriptionHandler:
        return CancelSubscriptionHandler(repo, event_bus)

    @provide(scope=Scope.REQUEST)
    def get_subscription_handler(
            self, repo: SQLAlchemySubscriptionRepository
    ) -> GetSubscriptionHandler:
        return GetSubscriptionHandler(repo)

    @provide(scope=Scope.REQUEST)
    def get_active_subscription_handler(
            self, repo: SQLAlchemySubscriptionRepository
    ) -> GetActiveSubscriptionHandler:
        return GetActiveSubscriptionHandler(repo)

class SubscriptionContextProvider(Provider):

    @provide(scope=Scope.REQUEST)
    async def subscription_context(
        self,
        request: Request,
        repo: SQLAlchemySubscriptionRepository,
    ) -> SubscriptionContext:
        # 헤더가 없으면 guest 사용자로 처리
        customer_name = request.headers.get("X-Customer-Name", "guest")

        sub = await repo.find_active_by_customer(customer_name)
        if sub is None or not sub.is_active():
            return SubscriptionContext.guest(customer_name)

        return SubscriptionContext(
            customer_name=customer_name,
            tier=sub.tier.value,    # "basic" / "premium"
            is_active=True,
        )

class PaymentsProvider(Provider):

    @provide(scope=Scope.REQUEST)
    def payment_repository(
        self, session: AsyncSession,
    ) -> SQLAlchemyPaymentRepository:
        return SQLAlchemyPaymentRepository(session)

    @provide(scope=Scope.REQUEST)
    def payment_gateway(self) -> FakePaymentGateway:
        """PG. 나중에 토스/이니시스 등 실제 PG로 교체 시 이 한 줄만 변경."""
        return FakePaymentGateway()

    @provide(scope=Scope.REQUEST)
    def discount_policy(
        self, sub_ctx: SubscriptionContext,
    ) -> DiscountPolicy:

        match sub_ctx.tier:
            case "premium":
                return SubscriptionDiscountPolicy(
                    rate=Decimal("0.10"),
                    discount_type="premium_subscription",
                )
            case "basic":
                return SubscriptionDiscountPolicy(
                    rate=Decimal("0.05"),
                    discount_type="basic_subscription",
                )
            case _:
                # "none" 또는 알 수 없는 tier → 할인 없음
                return NoDiscountPolicy()

    @provide(scope=Scope.REQUEST)
    def process_payment_handler(
        self,
        repo: SQLAlchemyPaymentRepository,
        gateway: FakePaymentGateway,
        discount_policy: DiscountPolicy,
        event_bus: EventBus,
    ) -> ProcessPaymentHandler:
        return ProcessPaymentHandler(repo, gateway, discount_policy, event_bus)

class ShippingProvider(Provider):
    """Shipping 모듈 의존성.

    ★ Phase 2의 PaymentsProvider와 동일한 패턴.
    SubscriptionContext를 받아 tier에 따라 정책을 분기 주입한다.
    """

    @provide(scope=Scope.REQUEST)
    def shipment_repository(
        self, session: AsyncSession,
    ) -> SQLAlchemyShipmentRepository:
        return SQLAlchemyShipmentRepository(session)

    @provide(scope=Scope.REQUEST)
    def shipping_fee_policy(
        self, sub_ctx: SubscriptionContext,
    ) -> ShippingFeePolicy:
        """★ 두 번째 정책 주입 진입점.

        Premium → 항상 무료
        Basic   → 50% 할인, 3만원↑ 무료
        그 외    → 기본 3,000원, 5만원↑ 무료
        """
        match sub_ctx.tier:
            case "premium":
                return PremiumShippingFeePolicy()
            case "basic":
                return BasicShippingFeePolicy()
            case _:
                return StandardShippingFeePolicy()

    @provide(scope=Scope.REQUEST)
    def update_shipment_status_handler(
        self,
        repo: SQLAlchemyShipmentRepository,
        event_bus: EventBus,
    ) -> UpdateShipmentStatusHandler:
        return UpdateShipmentStatusHandler(repo, event_bus)

def create_container() -> AsyncContainer:
    return make_async_container(
        AppProvider(),
        OrdersProvider(),
        SubscriptionsProvider(),
        SubscriptionContextProvider(),
        PaymentsProvider(),
        ShippingProvider(),
    )