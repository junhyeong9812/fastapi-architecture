from dishka import Provider, Scope, make_async_container, provide, AsyncContainer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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

class AppProvider(Provider):

    @provide(scope=Scope.APP)
    def config(self) -> AppConfig:
        return get_config()

    @provide(scope=Scope.APP)
    def engine(self, config: AppConfig) -> AsyncEngine:
        return create_engine(config)

    @provide(scope=Scope.App)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    @provide(scope=Scope.App)
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

def create_container() -> AsyncContainer:
    return make_async_container(
        AppProvider(), OrdersProvider(), SubscriptionsProvider(),
    )