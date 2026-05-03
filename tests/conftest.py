import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from dishka import make_async_container, Provider, Scope, provide

from app.shared.base_model import Base
from app.shared.event_bus import EventBus, InMemoryEventBus

# ORM 모델 import — 테이블 생성(create_all)에 필요
# import만 해도 Base.metadata에 등록됨
from app.orders.infrastructure.models import OrderModel, OrderItemModel  # noqa
from app.subscriptions.infrastructure.models import SubscriptionModel  # noqa

# Repository 구현체 + Handler 클래스
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

@pytest.fixture
async def async_engine():
    """SQLite 인메모리 엔진.

    "sqlite+aiosqlite://": 메모리에만 존재하는 DB.
    테스트가 끝나면 자동으로 사라진다.
    매 테스트마다 깨끗한 DB로 시작.
    """
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    # 모든 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # 테스트 후 정리
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
    """Dishka를 테스트용으로 오버라이드한 HTTP 클라이언트.

    ★ 핵심: 프로덕션 DI 컨테이너 대신 TestProvider를 사용.
    PostgreSQL 대신 SQLite, 실제 config 대신 테스트 설정.
    """
    from fastapi import FastAPI
    from dishka.integrations.fastapi import setup_dishka
    from app.orders.presentation.router import router as orders_router
    from app.subscriptions.presentation.router import router as subs_router

    class TestProvider(Provider):
        """테스트 전용 DI Provider.

        프로덕션의 AppProvider + OrdersProvider + SubscriptionsProvider를
        하나의 Provider로 합친 것.
        """
        @provide(scope=Scope.REQUEST)
        async def session(self) -> AsyncSession:
            """테스트용 세션. SQLite 인메모리 사용."""
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

    # 테스트용 FastAPI 앱 생성
    test_app = FastAPI()
    test_app.include_router(orders_router)
    test_app.include_router(subs_router)

    # 테스트용 DI 컨테이너
    container = make_async_container(TestProvider())
    setup_dishka(container, test_app)

    # httpx AsyncClient: 실제 HTTP 요청 없이 앱 내부에서 직접 호출
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client

    await container.close()