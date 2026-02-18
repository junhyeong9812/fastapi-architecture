# Phase 1: 뼈대 + Subscriptions + Orders 모듈

> **목표**: Hexagonal 구조가 돌아가는 것을 확인하고, domain 레이어의 순수성을 체감한다.

---

## 1.1 프로젝트 셋업

### 디렉토리 생성

```
shoptracker/
├── .venv/                       # python3.14 -m venv .venv
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── base_model.py
│       │   ├── subscription_context.py
│       │   ├── event_bus.py
│       │   ├── events.py
│       │   └── middleware.py
│       ├── orders/              # (1.3에서 구현)
│       └── subscriptions/       # (1.4에서 구현)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml
└── Dockerfile
```

### 생성할 파일 목록 (shared)

| 파일 | 역할 | 핵심 내용 |
|------|------|-----------|
| `pyproject.toml` | 프로젝트 메타, 빌드 설정 | setuptools, pytest 설정 |
| `requirements.txt` | 프로덕션 의존성 | fastapi, sqlalchemy, dishka 등 버전 핀 |
| `requirements-dev.txt` | 개발 의존성 | pytest, httpx, aiosqlite 추가 |
| `docker-compose.yml` | PostgreSQL + App | postgres:16-alpine, healthcheck |
| `Dockerfile` | 프로덕션 빌드 | python:3.14-slim 기반 |
| `alembic.ini` | Alembic 설정 | async URL 연결 |
| `alembic/env.py` | 마이그레이션 환경 | async_engine_from_config 사용 |

---

## 1.2 shared 모듈 구현

각 파일의 역할과 구현 핵심:

### `shared/config.py`

```
역할: 환경별 설정 관리
핵심:
  - pydantic_settings.BaseSettings 상속
  - DATABASE_URL, ENV, DEBUG 등 정의
  - .env 파일에서 자동 로드
  - get_config() 팩토리 함수 제공
```

### `shared/database.py`

```
역할: SQLAlchemy async 엔진 + 세션 팩토리
핵심:
  - create_async_engine(url, pool_pre_ping=True)
  - async_sessionmaker 반환
  - 엔진/세션은 여기서 생성, DI 컨테이너에서 주입
```

### `shared/base_model.py`

```
역할: SQLAlchemy DeclarativeBase
핵심:
  - class Base(DeclarativeBase): pass
  - 모든 ORM 모델이 이것을 상속
```

### `shared/subscription_context.py`

```
역할: 모듈 간 공유되는 구독 상태 DTO
핵심:
  - @dataclass(frozen=True) — 불변
  - customer_name, tier("none"/"basic"/"premium"), is_active
  - guest() 클래스메서드 — 미구독 기본값
  - ★ Payments, Shipping은 Subscription 엔티티를 모르고 이 DTO만 안다
```

### `shared/event_bus.py`

```
역할: 이벤트 버스 인터페이스 + 인메모리 구현
핵심:
  - EventBus(Protocol): publish(), subscribe() 정의
  - InMemoryEventBus: defaultdict(list)로 핸들러 관리
  - publish 시 등록된 핸들러 순차 호출
  - 핸들러 실패 시 로깅 후 계속 진행 (다른 핸들러에 영향 없도록)
  - ★ Protocol로 정의 → 나중에 Redis/Kafka 교체 가능
```

### `shared/events.py`

```
역할: 도메인 이벤트 계약(contract) 정의
핵심:
  - 모두 @dataclass(frozen=True)
  - Phase 1에서 정의할 이벤트:
    - OrderCreatedEvent (order_id, customer_name, total_amount, items_count, timestamp)
    - OrderCancelledEvent (order_id, reason, timestamp)
    - SubscriptionActivatedEvent (subscription_id, customer_name, tier, expires_at, timestamp)
    - SubscriptionExpiredEvent (subscription_id, customer_name, previous_tier, timestamp)
  - Phase 2에서 추가할 이벤트 (미리 자리만):
    - PaymentApprovedEvent, PaymentRejectedEvent
  - Phase 3에서 추가할 이벤트:
    - ShipmentCreatedEvent, ShipmentStatusChangedEvent
```

### `shared/middleware.py`

```
역할: structlog 기반 요청/응답 로깅
핵심:
  - BaseHTTPMiddleware 상속
  - 요청 시작/완료 시 method, path, status, elapsed_ms 로깅
```

---

## 1.3 Orders 모듈 구현

### 레이어 구조

```
orders/
├── domain/           # 순수 Python — 외부 의존 0
│   ├── value_objects.py
│   ├── entities.py
│   ├── exceptions.py
│   └── interfaces.py
├── application/      # Use Case 레이어
│   ├── commands.py
│   ├── queries.py
│   ├── command_handlers.py
│   ├── query_handlers.py
│   └── event_handlers.py   # (Phase 2에서 구현)
├── infrastructure/   # 외부 연결
│   ├── models.py
│   ├── mappers.py
│   └── repository.py
└── presentation/     # HTTP 인터페이스
    ├── schemas.py
    └── router.py
```

### domain/value_objects.py

```
역할: Money, OrderStatus 정의
핵심:
  Money:
    - __slots__ = ("amount", "currency")
    - Decimal 기반, 기본 통화 "KRW"
    - add, subtract, multiply, apply_rate 메서드 → 항상 새 인스턴스 반환 (불변)
    - is_positive, __eq__, __gt__, __ge__, __hash__ 구현
    - 통화 불일치 시 ValueError
  OrderStatus:
    - str Enum: CREATED, PAYMENT_PENDING, PAID, SHIPPING, DELIVERED, CANCELLED
    - can_transition_to(target) 메서드
    - _VALID_TRANSITIONS dict로 전이 규칙 정의:
      CREATED → {PAYMENT_PENDING, CANCELLED}
      PAYMENT_PENDING → {PAID, CANCELLED}
      PAID → {SHIPPING}         # ← PAID 이후 취소 불가
      SHIPPING → {DELIVERED}
      DELIVERED → {} (terminal)
      CANCELLED → {} (terminal)
```

### domain/entities.py

```
역할: Order, OrderItem 엔티티
핵심:
  OrderItem:
    - product_name, quantity, unit_price(Money)
    - subtotal property: unit_price.multiply(quantity)
  Order:
    - id(UUID), customer_name, items, status, total_amount, created_at, updated_at
    - ★ 팩토리 메서드 Order.create():
      - 이름 빈값 검증
      - items 최소 1개 검증
      - 각 item quantity > 0, unit_price > 0 검증
      - total_amount 자동 계산
      - 상태 CREATED로 시작
    - 상태 전이 메서드:
      - _transition_to(target): can_transition_to 검증 후 변경
      - mark_payment_pending, mark_paid, mark_shipping, mark_delivered, cancel
      - 전이 실패 시 InvalidStatusTransition 예외
  ★ 이 파일에 import fastapi / sqlalchemy 절대 없음
```

### domain/exceptions.py

```
역할: 주문 도메인 예외
핵심:
  - OrderError (base)
  - InvalidOrderError(reason) — 생성 규칙 위반
  - OrderNotFoundError(order_id) — 조회 실패
  - InvalidStatusTransition(current, target) — 상태 전이 위반
```

### domain/interfaces.py

```
역할: Repository Protocol (Output Port)
핵심:
  OrderRepositoryProtocol:
    - save(order), find_by_id(order_id), update(order)
  OrderReadRepositoryProtocol:
    - find_by_id(order_id)
    - list_orders(customer_name?, status?, page, size) → list[Order]
    - count_orders(customer_name?, status?) → int
  ★ Protocol로 정의 — 구현체를 모른다
  ★ Phase 1에서는 하나의 구현체가 둘 다 충족
```

### application/commands.py

```
역할: Command DTO (쓰기 의도 표현)
핵심:
  - OrderItemDTO(product_name, quantity, unit_price)
  - CreateOrderCommand(customer_name, items: list[OrderItemDTO])
  - CancelOrderCommand(order_id: str)
  - 모두 @dataclass(frozen=True)
```

### application/queries.py

```
역할: Query DTO (읽기 의도 표현)
핵심:
  - GetOrderQuery(order_id: str)
  - ListOrdersQuery(customer_name?, status?, page=1, size=20)
```

### application/command_handlers.py

```
역할: Command 처리 + 이벤트 발행
핵심:
  CreateOrderHandler:
    - 의존성: OrderRepositoryProtocol, EventBus
    - handle(command):
      1. command.items → OrderItem 변환 (Money 생성)
      2. Order.create() 호출
      3. order.mark_payment_pending() — 생성 즉시 결제 대기 상태로
      4. repo.save(order)
      5. event_bus.publish(OrderCreatedEvent)
      6. return order.id
  CancelOrderHandler:
    - 의존성: OrderRepositoryProtocol, EventBus
    - handle(command):
      1. repo.find_by_id()
      2. order.cancel() — 상태 전이 검증은 엔티티가 함
      3. repo.update()
      4. event_bus.publish(OrderCancelledEvent)
  ★ 핸들러는 Payments, Shipping을 import하지 않는다
```

### application/query_handlers.py

```
역할: Query 처리 (읽기 전용)
핵심:
  GetOrderHandler:
    - 의존성: OrderReadRepositoryProtocol (★ EventBus 없음 → CQRS 체감)
    - handle(query): find_by_id → 없으면 OrderNotFoundError
  ListOrdersHandler:
    - 의존성: OrderReadRepositoryProtocol
    - handle(query): list_orders + count_orders → PaginatedOrders 반환
```

### application/event_handlers.py

```
역할: 외부 이벤트 수신 핸들러 (Phase 2에서 구현)
핵심:
  - Phase 1에서는 빈 파일 (placeholder)
  - Phase 2에서 PaymentApprovedEvent → order.mark_paid() 추가
  - Phase 3에서 ShipmentStatusChangedEvent → order.mark_shipping/delivered 추가
```

### infrastructure/models.py

```
역할: SQLAlchemy ORM 모델
핵심:
  OrderModel:
    - id(UUID PK), customer_name, status, total_amount(Numeric), currency, created_at, updated_at
    - items 관계: relationship(cascade="all, delete-orphan", lazy="selectin")
  OrderItemModel:
    - id(autoincrement PK), order_id(FK), product_name, quantity, unit_price, currency
```

### infrastructure/mappers.py

```
역할: Entity ↔ ORM Model 변환
핵심:
  order_to_model(Order) → OrderModel:
    - Money.amount → Decimal, Money.currency → str
    - items도 각각 변환
  model_to_order(OrderModel) → Order:
    - Decimal → Money, str → OrderStatus(Enum)
  ★ 도메인 엔티티와 ORM 모델은 별개. 이 mapper가 두 세계를 연결
```

### infrastructure/repository.py

```
역할: SQLAlchemy Repository 구현체 (Driven Adapter)
핵심:
  SQLAlchemyOrderRepository:
    - __init__(session: AsyncSession)
    - save: order_to_model → session.add → flush
    - find_by_id: session.get → model_to_order
    - update: session.get → 필드 갱신 → flush
    - list_orders: select + where + order_by + offset/limit
    - count_orders: select(func.count)
  ★ OrderRepositoryProtocol과 OrderReadRepositoryProtocol을 동시에 충족
```

### presentation/schemas.py

```
역할: Pydantic v2 Request/Response DTO
핵심:
  Request:
    - OrderItemRequest(product_name, quantity>0, unit_price>0)
    - CreateOrderRequest(customer_name, items: min_length=1)
  Response:
    - OrderItemResponse(product_name, quantity, unit_price, subtotal)
    - OrderResponse(id, customer_name, status, total_amount, currency, items, created_at, updated_at)
    - OrderListResponse(items, total, page, size)
```

### presentation/router.py

```
역할: FastAPI APIRouter
핵심:
  - DishkaRoute 사용 (route_class=DishkaRoute)
  - FromDishka[Handler]로 핸들러 주입받음
  - _order_to_response 헬퍼로 Entity → Response 변환
  엔드포인트:
    POST /api/v1/orders/           → CreateOrderHandler → 201
    GET  /api/v1/orders/           → ListOrdersHandler → 200
    GET  /api/v1/orders/{order_id} → GetOrderHandler → 200 / 404
    POST /api/v1/orders/{order_id}/cancel → CancelOrderHandler → 200 / 400 / 404
  ★ 라우터는 얇다. 비즈니스 로직 없이 핸들러에 위임만
```

---

## 1.4 Subscriptions 모듈 구현

### 레이어 구조

```
subscriptions/
├── domain/
│   ├── entities.py
│   └── interfaces.py
├── application/
│   └── handlers.py       # commands + queries + handlers 한 파일 (규모가 작으므로)
├── infrastructure/
│   ├── models.py
│   ├── mappers.py
│   └── repository.py
└── presentation/
    ├── schemas.py
    └── router.py
```

### domain/entities.py

```
역할: Subscription 엔티티 + 관련 Enum/예외
핵심:
  SubscriptionTier(str, Enum):
    - NONE, BASIC, PREMIUM
  SubscriptionStatus(str, Enum):
    - ACTIVE, EXPIRED, CANCELLED
  예외:
    - SubscriptionError (base)
    - InvalidSubscriptionError(reason)
    - SubscriptionNotFoundError(subscription_id)
  Subscription:
    - id, customer_name, tier, status, started_at, expires_at
    - ★ 팩토리 메서드 Subscription.create():
      - 이름 빈값 검증
      - NONE 등급 생성 불가
      - duration_days=30 기본
      - 상태 ACTIVE로 시작
    - is_active(): ACTIVE이고 expires_at > now
      - timezone-naive 호환 처리 포함 (SQLite 대응)
    - cancel(): ACTIVE일 때만 → CANCELLED
    - expire(): → EXPIRED
```

### domain/interfaces.py

```
역할: Repository Protocol
핵심:
  SubscriptionRepositoryProtocol:
    - save, find_by_id, find_active_by_customer, update
```

### application/handlers.py

```
역할: Commands + Queries + Handlers (소규모이므로 한 파일)
핵심:
  Commands:
    - CreateSubscriptionCommand(customer_name, tier)
    - CancelSubscriptionCommand(subscription_id)
  Queries:
    - GetSubscriptionQuery(subscription_id)
    - GetActiveSubscriptionQuery(customer_name)
  CreateSubscriptionHandler:
    - 의존성: SubscriptionRepositoryProtocol, EventBus
    - handle:
      1. 기존 활성 구독 조회 → 있으면 expire() 처리
      2. Subscription.create()
      3. repo.save()
      4. event_bus.publish(SubscriptionActivatedEvent)
    - ★ 한 고객에 활성 구독 1개만 유지
  CancelSubscriptionHandler, GetSubscriptionHandler, GetActiveSubscriptionHandler
```

### infrastructure/ (models.py, mappers.py, repository.py)

```
역할: Orders와 동일한 패턴
핵심:
  SubscriptionModel: id, customer_name, tier, status, started_at, expires_at
  mapper: Subscription ↔ SubscriptionModel 변환
  repository: SQLAlchemy 구현체, find_active_by_customer는 status="active" + 최신순 1개
```

### presentation/ (schemas.py, router.py)

```
역할: API 인터페이스
핵심:
  엔드포인트:
    POST /api/v1/subscriptions/                    → 구독 생성 (201)
    GET  /api/v1/subscriptions/{id}                → 구독 상세 (200/404)
    GET  /api/v1/subscriptions/customer/{name}     → 활성 구독 조회 (200/null)
    POST /api/v1/subscriptions/{id}/cancel         → 구독 취소 (200/400/404)
  SubscriptionResponse에 is_active 필드 포함 (엔티티의 is_active() 호출)
```

---

## 1.5 DI 컨테이너 조립

### `shared/di_container.py`

```
역할: Dishka Provider로 모든 모듈의 의존성을 조립
핵심:
  AppProvider:
    - Scope.APP: config, engine, session_factory, event_bus
    - Scope.REQUEST: session (AsyncSession, commit/rollback 관리)
  OrdersProvider:
    - Scope.REQUEST: order_repository, order_read_repository
    - Scope.REQUEST: create_order_handler, cancel_order_handler, get_order_handler, list_orders_handler
  SubscriptionsProvider:
    - Scope.REQUEST: subscription_repository
    - Scope.REQUEST: 각 handler들
  create_container():
    - make_async_container(AppProvider(), OrdersProvider(), SubscriptionsProvider())
  ★ 이곳이 유일하게 "모든 모듈을 아는" 장소
```

---

## 1.6 main.py

```
역할: FastAPI 앱 엔트리포인트
핵심:
  - structlog 설정 (ConsoleRenderer for dev)
  - lifespan context manager (on_event 대신)
  - LoggingMiddleware 등록
  - Dishka setup_dishka(container, app)
  - include_router: orders, subscriptions
  - /health 엔드포인트
```

---

## 1.7 Alembic 설정

```
역할: DB 마이그레이션
핵심:
  alembic/env.py:
    - 모든 모듈의 models.py를 import (테이블 인식용)
    - async_engine_from_config 사용
    - target_metadata = Base.metadata
```

---

## 1.8 테스트

### tests/conftest.py

```
역할: 공통 fixture
핵심:
  - async_engine: SQLite 인메모리 ("sqlite+aiosqlite://")
  - db_session: 테스트마다 rollback
  - event_bus: InMemoryEventBus 인스턴스
  - async_client: Dishka 오버라이드한 TestClient
    - TestProvider 하나에 모든 의존성 정의
    - SQLite용 session_factory
    - 테스트 전용 EventBus 인스턴스 주입
  ★ PostgreSQL 없이 통합 테스트 가능 — Protocol 덕분
```

### tests/unit/ (DB 없음, 0.1초)

| 파일 | 테스트 내용 |
|------|------------|
| `test_money_value_object.py` | 생성, 사칙연산, 비율 적용, 통화 검증, 비교 연산 |
| `test_order_entity.py` | 정상 생성, 빈 항목 예외, 빈 이름 예외, 수량/가격 검증, 전체 상태 전이(happy path), 불가능한 전이 예외(PAID→CANCEL, CREATED→DELIVERED, DELIVERED terminal) |
| `test_subscription_entity.py` | 생성(BASIC/PREMIUM), NONE 생성 불가, 30일 기본, is_active 판정, 만료 판정, cancel, 비활성 cancel 예외 |

### tests/integration/ (SQLite 인메모리)

| 파일 | 테스트 내용 |
|------|------------|
| `test_order_flow.py` | POST 주문 생성(201), 복수 항목 합계, 빈 항목(422), GET 조회, 404, 목록 조회, 취소 |
| `test_subscription_flow.py` | POST 구독 생성(basic/premium), GET 조회, 활성 구독 조회, 업그레이드 시 기존 만료, 취소, 잘못된 tier(422) |

---

## 1.9 Phase 1 체감 체크포인트

```bash
# 1. domain/에 프레임워크 import 0건
grep -rn "import fastapi\|import sqlalchemy\|import dishka" src/app/orders/domain/
grep -rn "import fastapi\|import sqlalchemy\|import dishka" src/app/subscriptions/domain/

# 2. 단위 테스트 DB 없이 0.1초
pytest tests/unit -v

# 3. 모듈 간 직접 import 0건
grep -rn "from.*subscriptions\|import subscriptions" src/app/orders/
grep -rn "from.*orders\|import orders" src/app/subscriptions/

# 4. 통합 테스트 전체 통과
pytest tests/ -v
```

---

## 1.10 Phase 1 완료 기준

- [ ] shared 모듈 7파일 구현
- [ ] Orders 모듈 12파일 구현 (domain 4 + application 5 + infra 3 + presentation 2)
- [ ] Subscriptions 모듈 8파일 구현
- [ ] DI 컨테이너 연결
- [ ] main.py 앱 실행 가능
- [ ] 단위 테스트 35개 통과 (DB 없음)
- [ ] 통합 테스트 14개 통과 (SQLite 인메모리)
- [ ] 4개 체감 체크포인트 전부 통과