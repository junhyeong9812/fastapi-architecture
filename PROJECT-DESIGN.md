# 🏗️ FastAPI 모듈러 모놀리스 설계 문서

## 프로젝트명: **ShopTracker**

> 주문 → 결제 → 배송 흐름을 모듈러 모놀리스로 구현하며,
> FastAPI 클린 아키텍처의 핵심 패턴을 체감하는 학습 프로젝트

---

## 1. 프로젝트 목표

### 학습 목표 (이 프로젝트를 통해 체감할 것들)

| # | 패턴 | 체감 포인트 |
|---|------|------------|
| 1 | **Hexagonal Architecture** | 도메인에 FastAPI/SQLAlchemy import가 없는 걸 직접 확인 |
| 2 | **의존성 역전 (DIP)** | Repository를 Protocol로 정의하고, 구현체를 교체해보기 |
| 3 | **DI + 정책 주입** | 같은 결제 흐름인데 구독 등급에 따라 할인/배송비 정책이 바뀌는 것 |
| 4 | **내부 이벤트 버스** | 모듈 간 직접 import 없이 이벤트로만 소통 |
| 5 | **CQRS (간소화)** | 주문 생성(Command)과 주문 목록 조회(Query)의 모델 분리 |
| 6 | **Saga / 추적 도메인** | 주문→결제→배송 전체 흐름을 Tracking이 기록 |
| 7 | **횡단 관심사 설계** | 구독권이 결제 할인 + 배송비 할인에 모두 영향, 그러나 느슨하게 |
| 8 | **테스트** | 도메인 단위 테스트 (DB 없이), 통합 테스트 (TestClient) |
| 9 | **프로덕션 배포** | Docker Compose + Gunicorn + Uvicorn workers |

### 비학습 목표 (의도적으로 빼는 것들)

- 실제 PG사 연동 → **Fake Payment Gateway**로 대체
- 프론트엔드 → API만 구현 (Swagger UI로 테스트)
- 인증/인가 → 간소화 (API Key 수준, JWT까지는 안 감)
- 실제 배송 추적 → 상태 전이 시뮬레이션
- 구독 결제 자동 갱신 → 수동 생성/만료로 단순화

---

## 2. 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|-----------|
| **Framework** | FastAPI 0.129+ | 학습 대상 |
| **Python** | 3.12 | 2026 권장 버전 |
| **DB** | PostgreSQL 16 + asyncpg | 실무 표준, async 네이티브 |
| **ORM** | SQLAlchemy 2.0 (async) | 가장 성숙한 Python ORM |
| **Migration** | Alembic | SQLAlchemy 표준 마이그레이션 |
| **DI** | Dishka | 스코프 관리, 정책 주입 체감용 |
| **Validation** | Pydantic v2 | FastAPI 기본 |
| **Settings** | pydantic-settings | 환경별 설정 관리 |
| **Testing** | pytest + httpx (AsyncClient) | async 테스트 지원 |
| **Logging** | structlog (JSON) | 구조화된 로깅 |
| **Container** | Docker Compose | PostgreSQL + App 구성 |
| **ASGI** | Gunicorn + Uvicorn workers | 프로덕션 배포 |

---

## 3. 도메인 설계

### 3.1 Bounded Contexts (모듈)

```
┌──────────────────────────────────────────────────────────────┐
│                      ShopTracker App                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Orders    │  │  Payments   │  │  Shipping   │         │
│  │   (주문)    │  │   (결제)    │  │   (배송)    │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│         │          ┌─────┴─────┐          │                  │
│         │          │Subscription│          │                  │
│         │          │  (구독권)  │          │                  │
│         │          └─────┬─────┘          │                  │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                 ┌────────▼────────┐                          │
│                 │    Tracking     │                          │
│                 │   (추적/Saga)   │                          │
│                 └─────────────────┘                          │
│                          │                                   │
│                 ┌────────▼────────┐                          │
│                 │   Event Bus     │                          │
│                 │  (내부 메시징)   │                          │
│                 └─────────────────┘                          │
└──────────────────────────────────────────────────────────────┘
```

> **핵심 규칙**: 모듈 간 직접 import 금지.
> Payments는 Subscription을 import하지 않는다.
> 대신 DI가 구독 상태를 기반으로 적절한 **정책 객체**를 주입한다.

### 3.2 구독권이 다른 모듈에 영향을 주는 방식

```
┌──────────────┐
│ Subscription │  구독 등급 정보를 가진 유일한 소스
│    Module    │
└──────┬───────┘
       │
       │  SubscriptionContext (읽기 전용 DTO)
       │  → DI Container가 요청 시점에 조회
       │
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌──────────────┐                        ┌──────────────┐
│  Payments    │                        │  Shipping    │
│              │                        │              │
│ DiscountPolicy ← DI가 구독 등급에     │ ShippingFeePolicy ← DI가 구독 등급에
│   따라 주입      맞는 정책 주입       │   따라 주입        맞는 정책 주입
└──────────────┘                        └──────────────┘
```

> **아키텍처 학습 포인트**: Payments와 Shipping은 `Subscription`을 전혀 모른다.
> DI 컨테이너가 "현재 고객의 구독 등급"을 기반으로 올바른 정책 객체를 조립해서 넣어줄 뿐이다.
> 이것이 **느슨한 결합 + 정책 기반 주입**의 핵심.

### 3.3 각 모듈의 도메인 엔티티

#### Subscriptions (구독)

```python
# 엔티티
class Subscription:
    id: UUID
    customer_name: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    started_at: datetime
    expires_at: datetime

    def is_active(self) -> bool:
        """만료 전이고 ACTIVE 상태인지"""
        return (
            self.status == SubscriptionStatus.ACTIVE
            and self.expires_at > datetime.now(UTC)
        )

# 구독 등급
class SubscriptionTier(str, Enum):
    NONE = "none"            # 미구독 (기본)
    BASIC = "basic"          # 기본 구독: 결제 5% 할인, 배송비 50% 할인
    PREMIUM = "premium"      # 프리미엄 구독: 결제 10% 할인, 배송비 무료

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
```

**구독 등급별 혜택 정리:**

| 혜택 | NONE (미구독) | BASIC | PREMIUM |
|------|:---:|:---:|:---:|
| 결제 할인 | 0% | 5% | 10% |
| 배송비 | 정상 (3,000원) | 50% 할인 (1,500원) | 무료 |
| 무료배송 기준 | 50,000원 이상 | 30,000원 이상 | 항상 무료 |

**비즈니스 규칙 (도메인 레이어):**
- 구독은 생성 시 시작일 + 만료일 지정 (30일 단위)
- 만료된 구독은 `is_active() == False`
- 한 고객에 동시에 활성 구독 1개만 허용
- 상위 등급으로 변경 시 기존 구독 만료 처리 → 새 구독 생성

#### SubscriptionContext (모듈 간 공유 DTO)

```python
# shared/subscription_context.py — 모듈 간 공유되는 읽기 전용 DTO
@dataclass(frozen=True)
class SubscriptionContext:
    """구독 상태를 요약한 불변 DTO.
    Payments, Shipping 등 다른 모듈은 이것만 알면 된다.
    Subscription 엔티티 자체는 모른다."""
    customer_name: str
    tier: str                    # "none", "basic", "premium"
    is_active: bool
```

> **설계 포인트**: `SubscriptionContext`는 `shared/`에 있지만 Subscription 모듈의 도메인 엔티티가 아니다.
> 다른 모듈이 구독 "상태"를 참고할 수 있게 하는 **얇은 계약(thin contract)**이다.

#### Orders (주문)

```python
# 엔티티
class Order:
    id: UUID
    customer_name: str
    items: list[OrderItem]
    status: OrderStatus
    total_amount: Money          # 상품 금액 합계
    shipping_fee: Money          # 배송비 (구독 정책 반영)
    discount_amount: Money       # 구독 할인 금액
    final_amount: Money          # 최종 결제 금액 (total + shipping - discount)
    created_at: datetime

class OrderItem:
    product_name: str
    quantity: int
    unit_price: Money

# Value Object
class Money:
    amount: Decimal
    currency: str = "KRW"

    def add(self, other: Money) -> Money: ...
    def subtract(self, other: Money) -> Money: ...
    def multiply(self, factor: int) -> Money: ...
    def apply_rate(self, rate: Decimal) -> Money: ...

    def __eq__(self, other): ...
    def __gt__(self, other): ...

# 상태 전이
class OrderStatus(str, Enum):
    CREATED = "created"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
```

**비즈니스 규칙:**
- 주문 항목은 최소 1개 이상
- 총 금액은 0원 초과
- `PAID` 이후에는 취소 불가
- 상태 전이 유효성 검증: `CREATED → PAYMENT_PENDING` 가능, `CREATED → DELIVERED` 불가
- `final_amount = total_amount + shipping_fee - discount_amount`

#### Payments (결제)

```python
# 엔티티
class Payment:
    id: UUID
    order_id: UUID
    original_amount: Money       # 할인 전 금액
    discount_amount: Money       # 정책 적용 할인 금액
    final_amount: Money          # 최종 결제 금액
    method: PaymentMethod
    status: PaymentStatus
    applied_discount_type: str   # "none", "basic_subscription", "premium_subscription"
    processed_at: datetime | None

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    VIRTUAL_ACCOUNT = "virtual_account"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
```

**비즈니스 규칙 + 정책 객체:**
- `DiscountPolicy` (인터페이스) → `SubscriptionDiscountPolicy`, `NoDiscountPolicy`
- `PaymentValidationPolicy` → 결제 수단별 한도 (카드: 100만원, 계좌이체: 500만원)
- `FakePaymentGateway` → 90% 승인 / 10% 거절
- **Payments는 "왜 5% 할인인지" 모른다** — 주입받은 Policy가 할인율을 결정

#### Shipping (배송)

```python
# 엔티티
class Shipment:
    id: UUID
    order_id: UUID
    status: ShipmentStatus
    address: Address
    shipping_fee: Money          # 정책 적용 후 배송비
    original_fee: Money          # 정책 적용 전 기본 배송비
    fee_discount_type: str       # "none", "basic_half", "premium_free"
    tracking_number: str | None
    estimated_delivery: date | None

class Address:
    street: str
    city: str
    zip_code: str

class ShipmentStatus(str, Enum):
    PREPARING = "preparing"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
```

**비즈니스 규칙 + 정책 객체:**
- `ShippingFeePolicy` (인터페이스) → `StandardShippingFeePolicy`, `SubscriptionShippingFeePolicy`
- 기본 배송비: 3,000원
- 무료배송 기준금액도 구독 등급에 따라 달라짐
- **Shipping은 "왜 무료인지" 모른다** — 주입받은 Policy가 배송비를 결정

#### Tracking (추적/Saga)

```python
class OrderTracking:
    id: UUID
    order_id: UUID
    customer_name: str
    subscription_tier: str       # 추적 시점의 구독 등급 스냅샷
    events: list[TrackingEvent]
    current_phase: TrackingPhase
    started_at: datetime
    completed_at: datetime | None

class TrackingEvent:
    event_type: str
    timestamp: datetime
    module: str
    detail: dict                 # 할인 정보, 배송비 정보 등 포함

class TrackingPhase(str, Enum):
    ORDER_PLACED = "order_placed"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_COMPLETED = "payment_completed"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    FAILED = "failed"
```

### 3.4 이벤트 흐름

```
[고객 주문 생성]
       │
       ▼
  ┌──────────┐   1. OrderCreatedEvent     ┌──────────────┐
  │  Orders  │ ────────────────────────▶  │ Subscription │  구독 상태 조회
  │          │                             │   (via DI)   │
  └──────────┘                             └──────┬───────┘
       │                                          │
       │   OrderCreatedEvent                      │ SubscriptionContext
       │                                          ▼
       │                                   ┌─────────────┐
       ├──────────────────────────────────▶│  Payments   │
       │                                   │ 정책 주입:   │
       │                                   │ - 할인율 결정 │
       │                                   │ - Fake 결제  │
       │                                   └──────┬──────┘
       │                                          │
       │                               ┌──────────┴──────────┐
       │                               ▼                     ▼
       │                    PaymentApprovedEvent    PaymentRejectedEvent
       │                               │                     │
       │                    ┌──────────┴───┐          ┌──────┴──────┐
       │                    ▼              ▼          ▼             ▼
       │              ┌──────────┐  ┌──────────┐ ┌────────┐  ┌──────────┐
       │              │ Shipping │  │ Tracking │ │ Orders │  │ Tracking │
       │              │ 정책주입: │  │ 기록     │ │→CANCEL │  │ 기록:    │
       │              │ 배송비   │  └──────────┘ └────────┘  │ failed   │
       │              │ 결정     │                           └──────────┘
       │              └────┬─────┘
       │                   ▼
       │        ShipmentCreatedEvent
       │                   │
       │              ┌────┴────┐
       │              ▼         ▼
       │         ┌────────┐ ┌──────────┐
       │         │ Orders │ │ Tracking │
       │         │→SHIPPING│ │ 기록     │
       │         └────────┘ └──────────┘
       │
       │   OrderCreatedEvent
       ├──────────────────────────────────▶ ┌──────────┐
       │                                    │ Tracking │
       │                                    │ 기록:    │
       │                                    │ 주문생성 │
       │                                    └──────────┘
```

### 3.5 이벤트 정의

```python
# shared/events.py — 모든 모듈이 공유하는 이벤트 계약

@dataclass(frozen=True)
class OrderCreatedEvent:
    order_id: UUID
    customer_name: str
    total_amount: Decimal
    items_count: int
    timestamp: datetime

@dataclass(frozen=True)
class PaymentApprovedEvent:
    payment_id: UUID
    order_id: UUID
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    applied_discount_type: str   # "none", "basic_subscription", "premium_subscription"
    method: str
    timestamp: datetime

@dataclass(frozen=True)
class PaymentRejectedEvent:
    payment_id: UUID
    order_id: UUID
    reason: str
    timestamp: datetime

@dataclass(frozen=True)
class ShipmentCreatedEvent:
    shipment_id: UUID
    order_id: UUID
    shipping_fee: Decimal
    fee_discount_type: str       # "none", "basic_half", "premium_free"
    tracking_number: str | None
    timestamp: datetime

@dataclass(frozen=True)
class ShipmentStatusChangedEvent:
    shipment_id: UUID
    order_id: UUID
    new_status: str
    timestamp: datetime

@dataclass(frozen=True)
class SubscriptionActivatedEvent:
    subscription_id: UUID
    customer_name: str
    tier: str
    expires_at: datetime
    timestamp: datetime

@dataclass(frozen=True)
class SubscriptionExpiredEvent:
    subscription_id: UUID
    customer_name: str
    previous_tier: str
    timestamp: datetime
```

---

## 4. 아키텍처 설계

### 4.1 각 모듈의 내부 구조 (Hexagonal)

```
orders/                           # 하나의 Bounded Context
├── domain/                       # 🎯 핵심: 순수 Python, 외부 의존 없음
│   ├── entities.py               # Order, OrderItem
│   ├── value_objects.py          # Money, OrderStatus
│   ├── exceptions.py             # OrderNotFoundError, InvalidStatusTransition
│   └── interfaces.py             # OrderRepositoryProtocol (Output Port)
│
├── application/                  # 🔄 Use Cases: 도메인 조율
│   ├── commands.py               # CreateOrderCommand, CancelOrderCommand
│   ├── queries.py                # GetOrderQuery, ListOrdersQuery
│   ├── command_handlers.py       # CreateOrderHandler (Event Bus 사용)
│   ├── query_handlers.py         # GetOrderHandler (읽기 전용)
│   └── event_handlers.py         # 외부 이벤트에 대한 반응 (PaymentApproved → 상태변경)
│
├── infrastructure/               # 🔧 외부 세계 연결
│   ├── models.py                 # SQLAlchemy ORM 모델 (OrderModel)
│   ├── repository.py             # SQLAlchemyOrderRepository
│   └── mappers.py                # Entity ↔ ORM Model 변환
│
└── presentation/                 # 🌐 HTTP 인터페이스
    ├── router.py                 # FastAPI APIRouter
    └── schemas.py                # Pydantic v2 Request/Response DTO
```

> **의존성 방향 검증**: `domain/` 폴더에서 `grep -r "import fastapi\|import sqlalchemy\|import dishka"` → 결과 0건이어야 함

### 4.2 DI 설계 (Dishka) — 구독 기반 정책 주입

```python
# shared/di_container.py

class SharedProvider(Provider):
    """모듈 공통 의존성"""

    @provide(scope=Scope.REQUEST)
    async def db_session(self, engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
        session = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()

    @provide(scope=Scope.APP)
    def event_bus(self) -> EventBus:
        return InMemoryEventBus()


class SubscriptionProvider(Provider):
    """구독 모듈 의존성"""

    @provide(scope=Scope.REQUEST)
    def subscription_repository(self, session: AsyncSession) -> SubscriptionRepositoryProtocol:
        return SQLAlchemySubscriptionRepository(session)

    @provide(scope=Scope.REQUEST)
    async def subscription_context(
        self, repo: SubscriptionRepositoryProtocol, request: Request
    ) -> SubscriptionContext:
        """요청에서 customer_name을 꺼내 구독 상태를 조회.
        다른 모듈은 이 SubscriptionContext만 받으면 된다."""
        customer_name = request.headers.get("X-Customer-Name", "guest")
        subscription = await repo.find_active_by_customer(customer_name)
        if subscription and subscription.is_active():
            return SubscriptionContext(
                customer_name=customer_name,
                tier=subscription.tier.value,
                is_active=True,
            )
        return SubscriptionContext(
            customer_name=customer_name, tier="none", is_active=False
        )


class PaymentsProvider(Provider):
    """결제 모듈 의존성 — 구독 상태에 따라 정책이 달라진다"""

    @provide(scope=Scope.REQUEST)
    def payment_gateway(self) -> PaymentGatewayProtocol:
        return FakePaymentGateway()

    @provide(scope=Scope.REQUEST)
    def discount_policy(self, sub_ctx: SubscriptionContext) -> DiscountPolicy:
        """★ 핵심 학습 포인트:
        Payments 모듈은 Subscription을 import하지 않는다.
        DI가 SubscriptionContext를 보고 적절한 정책을 조립해준다."""
        match sub_ctx.tier:
            case "premium":
                return SubscriptionDiscountPolicy(
                    rate=Decimal("0.10"), discount_type="premium_subscription"
                )
            case "basic":
                return SubscriptionDiscountPolicy(
                    rate=Decimal("0.05"), discount_type="basic_subscription"
                )
            case _:
                return NoDiscountPolicy()

    @provide(scope=Scope.REQUEST)
    def validation_policy(self) -> PaymentValidationPolicy:
        return StandardPaymentValidationPolicy()

    @provide(scope=Scope.REQUEST)
    def process_payment_handler(
        self,
        repo: PaymentRepositoryProtocol,
        gateway: PaymentGatewayProtocol,
        discount: DiscountPolicy,
        validation: PaymentValidationPolicy,
        event_bus: EventBus,
    ) -> ProcessPaymentHandler:
        return ProcessPaymentHandler(repo, gateway, discount, validation, event_bus)


class ShippingProvider(Provider):
    """배송 모듈 의존성 — 구독 상태에 따라 배송비 정책이 달라진다"""

    @provide(scope=Scope.REQUEST)
    def shipping_fee_policy(self, sub_ctx: SubscriptionContext) -> ShippingFeePolicy:
        """★ 핵심 학습 포인트:
        Shipping 모듈도 Subscription을 import하지 않는다.
        DI가 SubscriptionContext를 보고 적절한 배송비 정책을 조립해준다."""
        match sub_ctx.tier:
            case "premium":
                return PremiumShippingFeePolicy()     # 항상 무료
            case "basic":
                return BasicShippingFeePolicy()       # 50% 할인, 3만원 이상 무료
            case _:
                return StandardShippingFeePolicy()    # 3,000원, 5만원 이상 무료

    @provide(scope=Scope.REQUEST)
    def create_shipment_handler(
        self,
        repo: ShipmentRepositoryProtocol,
        fee_policy: ShippingFeePolicy,
        event_bus: EventBus,
    ) -> CreateShipmentHandler:
        return CreateShipmentHandler(repo, fee_policy, event_bus)
```

### 4.3 정책 객체 설계 — 결제 할인

```python
# payments/domain/interfaces.py

class DiscountPolicy(Protocol):
    """할인 정책 인터페이스 — 구현체는 DI로 주입"""
    def calculate_discount(self, amount: Money) -> DiscountResult: ...

@dataclass(frozen=True)
class DiscountResult:
    discount_amount: Money
    discount_type: str           # "none", "basic_subscription", "premium_subscription"

class PaymentGatewayProtocol(Protocol):
    async def process(self, payment: Payment) -> GatewayResult: ...

class PaymentValidationPolicy(Protocol):
    def validate(self, method: PaymentMethod, amount: Money) -> None: ...
```

```python
# payments/domain/policies.py

class SubscriptionDiscountPolicy:
    """구독 할인 — rate와 type을 DI에서 주입받음.
    이 클래스는 '구독'이라는 단어를 알지만, Subscription 모듈은 import하지 않는다."""
    def __init__(self, rate: Decimal, discount_type: str):
        self.rate = rate
        self.discount_type = discount_type

    def calculate_discount(self, amount: Money) -> DiscountResult:
        return DiscountResult(
            discount_amount=amount.apply_rate(self.rate),
            discount_type=self.discount_type,
        )

class NoDiscountPolicy:
    def calculate_discount(self, amount: Money) -> DiscountResult:
        return DiscountResult(
            discount_amount=Money(Decimal("0")),
            discount_type="none",
        )
```

### 4.4 정책 객체 설계 — 배송비

```python
# shipping/domain/interfaces.py

class ShippingFeePolicy(Protocol):
    """배송비 정책 인터페이스"""
    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult: ...

@dataclass(frozen=True)
class ShippingFeeResult:
    fee: Money
    original_fee: Money          # 할인 전 기본 배송비
    discount_type: str           # "none", "basic_half", "premium_free"
    reason: str                  # "기본 배송비", "구독 할인", "무료배송 기준 충족" 등
```

```python
# shipping/domain/policies.py

BASE_SHIPPING_FEE = Money(Decimal("3000"))

class StandardShippingFeePolicy:
    """미구독자: 3,000원, 50,000원 이상 무료"""
    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        if order_amount >= Money(Decimal("50000")):
            return ShippingFeeResult(
                fee=Money(Decimal("0")),
                original_fee=BASE_SHIPPING_FEE,
                discount_type="none",
                reason="50,000원 이상 무료배송",
            )
        return ShippingFeeResult(
            fee=BASE_SHIPPING_FEE,
            original_fee=BASE_SHIPPING_FEE,
            discount_type="none",
            reason="기본 배송비",
        )

class BasicShippingFeePolicy:
    """Basic 구독: 50% 할인, 30,000원 이상 무료"""
    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        if order_amount >= Money(Decimal("30000")):
            return ShippingFeeResult(
                fee=Money(Decimal("0")),
                original_fee=BASE_SHIPPING_FEE,
                discount_type="basic_half",
                reason="Basic 구독 30,000원 이상 무료배송",
            )
        return ShippingFeeResult(
            fee=Money(Decimal("1500")),
            original_fee=BASE_SHIPPING_FEE,
            discount_type="basic_half",
            reason="Basic 구독 배송비 50% 할인",
        )

class PremiumShippingFeePolicy:
    """Premium 구독: 항상 무료"""
    def calculate_fee(self, order_amount: Money) -> ShippingFeeResult:
        return ShippingFeeResult(
            fee=Money(Decimal("0")),
            original_fee=BASE_SHIPPING_FEE,
            discount_type="premium_free",
            reason="Premium 구독 무료배송",
        )
```

### 4.5 Fake Payment Gateway

```python
# payments/infrastructure/fake_gateway.py

class FakePaymentGateway:
    """90% 승인, 10% 거절하는 Fake 게이트웨이"""

    async def process(self, payment: Payment) -> GatewayResult:
        await asyncio.sleep(0.3)  # 네트워크 지연 시뮬레이션

        if random.random() < 0.9:
            return GatewayResult(
                success=True,
                transaction_id=str(uuid4()),
                message="Payment approved",
            )
        return GatewayResult(
            success=False,
            transaction_id=None,
            message="Insufficient funds",
        )
```

### 4.6 이벤트 버스 (인메모리)

```python
# shared/event_bus.py

class EventBus(Protocol):
    """나중에 Kafka/Redis로 교체 가능"""
    async def publish(self, event: object) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...

class InMemoryEventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: object) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception as e:
                logger.error("event_handler_failed",
                           event=type(event).__name__, error=str(e))
```

### 4.7 CQRS 적용 (간소화)

Command/Query 핸들러를 분리하되, DB는 공유합니다.

```python
# 예: orders/application/command_handlers.py
class CreateOrderHandler:
    def __init__(self, repo: OrderRepositoryProtocol, event_bus: EventBus):
        self.repo = repo
        self.event_bus = event_bus

    async def handle(self, command: CreateOrderCommand) -> UUID:
        order = Order.create(
            customer_name=command.customer_name,
            items=command.items,
        )
        await self.repo.save(order)
        await self.event_bus.publish(OrderCreatedEvent(...))
        return order.id

# 예: orders/application/query_handlers.py
class ListOrdersHandler:
    def __init__(self, repo: OrderReadRepositoryProtocol):
        self.repo = repo     # EventBus 의존 없음!

    async def handle(self, query: ListOrdersQuery) -> PaginatedResult[OrderSummary]:
        return await self.repo.list_orders(
            status=query.status, page=query.page, size=query.size
        )
```

---

## 5. 프로젝트 디렉토리 구조

```
shoptracker/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic/
│   ├── alembic.ini
│   └── versions/
├── tests/
│   ├── conftest.py                 # 공통 fixture (DB, EventBus, DI override)
│   ├── unit/                       # 🧪 DB 없음, 순수 도메인 테스트
│   │   ├── test_order_entity.py
│   │   ├── test_money_value_object.py
│   │   ├── test_status_transitions.py
│   │   ├── test_discount_policies.py
│   │   ├── test_shipping_fee_policies.py
│   │   └── test_subscription_entity.py
│   ├── integration/                # 🔗 DB + 이벤트 통합 테스트
│   │   ├── test_order_flow.py
│   │   ├── test_payment_with_subscription.py
│   │   ├── test_shipping_with_subscription.py
│   │   └── test_full_saga.py
│   └── e2e/                        # 🌐 API 엔드포인트 테스트
│       └── test_api.py
└── src/
    └── app/
        ├── main.py                 # FastAPI 앱 + lifespan + 이벤트 핸들러 등록
        ├── shared/
        │   ├── config.py           # pydantic-settings
        │   ├── database.py         # async engine, session
        │   ├── event_bus.py        # InMemoryEventBus
        │   ├── events.py           # 도메인 이벤트 정의
        │   ├── subscription_context.py  # SubscriptionContext DTO
        │   ├── di_container.py     # Dishka Provider 전체 조립
        │   ├── base_model.py       # SQLAlchemy DeclarativeBase
        │   └── middleware.py       # structlog 로깅 미들웨어
        │
        ├── orders/                 # 📦 주문 모듈
        │   ├── domain/
        │   │   ├── entities.py
        │   │   ├── value_objects.py
        │   │   ├── exceptions.py
        │   │   └── interfaces.py
        │   ├── application/
        │   │   ├── commands.py
        │   │   ├── queries.py
        │   │   ├── command_handlers.py
        │   │   ├── query_handlers.py
        │   │   └── event_handlers.py
        │   ├── infrastructure/
        │   │   ├── models.py
        │   │   ├── repository.py
        │   │   └── mappers.py
        │   └── presentation/
        │       ├── router.py
        │       └── schemas.py
        │
        ├── payments/               # 💳 결제 모듈
        │   ├── domain/
        │   │   ├── entities.py
        │   │   ├── value_objects.py
        │   │   ├── policies.py          # DiscountPolicy 구현체들
        │   │   ├── exceptions.py
        │   │   └── interfaces.py        # Gateway, Policy Protocol
        │   ├── application/
        │   │   ├── commands.py
        │   │   ├── command_handlers.py
        │   │   └── event_handlers.py
        │   ├── infrastructure/
        │   │   ├── models.py
        │   │   ├── repository.py
        │   │   ├── fake_gateway.py
        │   │   └── mappers.py
        │   └── presentation/
        │       ├── router.py
        │       └── schemas.py
        │
        ├── shipping/               # 🚚 배송 모듈
        │   ├── domain/
        │   │   ├── entities.py
        │   │   ├── value_objects.py
        │   │   ├── policies.py          # ShippingFeePolicy 구현체들
        │   │   ├── exceptions.py
        │   │   └── interfaces.py
        │   ├── application/
        │   │   ├── commands.py
        │   │   ├── command_handlers.py
        │   │   └── event_handlers.py
        │   ├── infrastructure/
        │   │   ├── models.py
        │   │   ├── repository.py
        │   │   └── mappers.py
        │   └── presentation/
        │       ├── router.py
        │       └── schemas.py
        │
        ├── subscriptions/          # 🎫 구독 모듈
        │   ├── domain/
        │   │   ├── entities.py          # Subscription, SubscriptionTier
        │   │   ├── exceptions.py
        │   │   └── interfaces.py
        │   ├── application/
        │   │   ├── commands.py          # CreateSubscription, CancelSubscription
        │   │   ├── queries.py           # GetActiveSubscription
        │   │   ├── command_handlers.py
        │   │   ├── query_handlers.py
        │   │   └── event_handlers.py
        │   ├── infrastructure/
        │   │   ├── models.py
        │   │   ├── repository.py
        │   │   └── mappers.py
        │   └── presentation/
        │       ├── router.py
        │       └── schemas.py
        │
        └── tracking/               # 📊 추적 모듈 (Saga)
            ├── domain/
            │   ├── entities.py
            │   ├── exceptions.py
            │   └── interfaces.py
            ├── application/
            │   ├── queries.py
            │   ├── query_handlers.py
            │   └── event_handlers.py    # 모든 이벤트를 구독
            ├── infrastructure/
            │   ├── models.py
            │   ├── repository.py
            │   └── mappers.py
            └── presentation/
                ├── router.py
                └── schemas.py
```

---

## 6. API 엔드포인트 설계

### Subscriptions (`/api/v1/subscriptions`)

| Method | Path | 설명 | 유형 |
|--------|------|------|------|
| `POST` | `/api/v1/subscriptions` | 구독 생성 (tier, customer_name) | Command |
| `GET` | `/api/v1/subscriptions/{subscription_id}` | 구독 상세 | Query |
| `GET` | `/api/v1/subscriptions/customer/{customer_name}` | 고객의 활성 구독 조회 | Query |
| `POST` | `/api/v1/subscriptions/{subscription_id}/cancel` | 구독 취소 | Command |

### Orders (`/api/v1/orders`)

| Method | Path | 설명 | 유형 |
|--------|------|------|------|
| `POST` | `/api/v1/orders` | 주문 생성 | Command |
| `GET` | `/api/v1/orders` | 주문 목록 (필터, 페이지네이션) | Query |
| `GET` | `/api/v1/orders/{order_id}` | 주문 상세 (할인/배송비 내역 포함) | Query |
| `POST` | `/api/v1/orders/{order_id}/cancel` | 주문 취소 | Command |

### Payments (`/api/v1/payments`)

| Method | Path | 설명 | 유형 |
|--------|------|------|------|
| `GET` | `/api/v1/payments/{payment_id}` | 결제 상세 (할인 내역 포함) | Query |
| `GET` | `/api/v1/payments/order/{order_id}` | 주문별 결제 조회 | Query |

### Shipping (`/api/v1/shipping`)

| Method | Path | 설명 | 유형 |
|--------|------|------|------|
| `GET` | `/api/v1/shipping/{shipment_id}` | 배송 상세 (배송비 내역 포함) | Query |
| `GET` | `/api/v1/shipping/order/{order_id}` | 주문별 배송 조회 | Query |
| `POST` | `/api/v1/shipping/{shipment_id}/update-status` | 배송 상태 변경 (시뮬레이션) | Command |

### Tracking (`/api/v1/tracking`)

| Method | Path | 설명 | 유형 |
|--------|------|------|------|
| `GET` | `/api/v1/tracking/order/{order_id}` | 주문 전체 여정 (할인/배송비 포함) | Query |
| `GET` | `/api/v1/tracking/order/{order_id}/timeline` | 타임라인 형태 | Query |

---

## 7. 테스트 전략

### 7.1 단위 테스트 — DB 없음

```python
# tests/unit/test_discount_policies.py

def test_premium_subscription_10_percent_discount():
    """Premium 구독자는 10% 할인"""
    policy = SubscriptionDiscountPolicy(
        rate=Decimal("0.10"), discount_type="premium_subscription"
    )
    result = policy.calculate_discount(Money(Decimal("100000")))
    assert result.discount_amount == Money(Decimal("10000"))
    assert result.discount_type == "premium_subscription"

def test_basic_subscription_5_percent_discount():
    """Basic 구독자는 5% 할인"""
    policy = SubscriptionDiscountPolicy(
        rate=Decimal("0.05"), discount_type="basic_subscription"
    )
    result = policy.calculate_discount(Money(Decimal("100000")))
    assert result.discount_amount == Money(Decimal("5000"))

def test_no_subscription_no_discount():
    """미구독자는 할인 없음"""
    policy = NoDiscountPolicy()
    result = policy.calculate_discount(Money(Decimal("100000")))
    assert result.discount_amount == Money(Decimal("0"))
    assert result.discount_type == "none"
```

```python
# tests/unit/test_shipping_fee_policies.py

def test_standard_shipping_fee():
    """미구독자: 3,000원 배송비"""
    policy = StandardShippingFeePolicy()
    result = policy.calculate_fee(Money(Decimal("30000")))
    assert result.fee == Money(Decimal("3000"))

def test_standard_free_shipping_over_50000():
    """미구독자: 50,000원 이상 무료배송"""
    policy = StandardShippingFeePolicy()
    result = policy.calculate_fee(Money(Decimal("50000")))
    assert result.fee == Money(Decimal("0"))

def test_basic_half_shipping_fee():
    """Basic 구독: 1,500원 (50% 할인)"""
    policy = BasicShippingFeePolicy()
    result = policy.calculate_fee(Money(Decimal("20000")))
    assert result.fee == Money(Decimal("1500"))

def test_basic_free_shipping_over_30000():
    """Basic 구독: 30,000원 이상 무료배송"""
    policy = BasicShippingFeePolicy()
    result = policy.calculate_fee(Money(Decimal("30000")))
    assert result.fee == Money(Decimal("0"))

def test_premium_always_free_shipping():
    """Premium 구독: 항상 무료"""
    policy = PremiumShippingFeePolicy()
    result = policy.calculate_fee(Money(Decimal("1000")))
    assert result.fee == Money(Decimal("0"))
    assert result.discount_type == "premium_free"
```

```python
# tests/unit/test_subscription_entity.py

def test_active_subscription():
    """만료 전 + ACTIVE 상태면 활성"""
    sub = Subscription(
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        expires_at=datetime.now(UTC) + timedelta(days=15),
    )
    assert sub.is_active() is True

def test_expired_subscription():
    """만료일 지나면 비활성"""
    sub = Subscription(
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    assert sub.is_active() is False
```

### 7.2 통합 테스트 — 구독 + 결제/배송 정책 연동

```python
# tests/integration/test_payment_with_subscription.py

async def test_premium_subscriber_gets_10_percent_discount(
    async_client: AsyncClient,
):
    """Premium 구독자가 주문하면 결제 시 10% 할인 적용"""
    # 1. Premium 구독 생성
    await async_client.post("/api/v1/subscriptions", json={
        "customer_name": "홍길동",
        "tier": "premium",
    })

    # 2. 주문 생성 (X-Customer-Name 헤더로 고객 식별)
    response = await async_client.post(
        "/api/v1/orders",
        json={
            "customer_name": "홍길동",
            "items": [{"product_name": "노트북", "quantity": 1, "unit_price": 1000000}],
        },
        headers={"X-Customer-Name": "홍길동"},
    )
    order_id = response.json()["id"]
    await asyncio.sleep(1)  # 이벤트 처리 대기

    # 3. 결제 확인: 10% 할인 적용되었는지
    payment = await async_client.get(f"/api/v1/payments/order/{order_id}")
    data = payment.json()
    assert data["applied_discount_type"] == "premium_subscription"
    assert data["discount_amount"] == 100000   # 100만원의 10%

async def test_no_subscription_no_discount(async_client: AsyncClient):
    """미구독자는 할인 없이 전액 결제"""
    response = await async_client.post(
        "/api/v1/orders",
        json={
            "customer_name": "미구독자",
            "items": [{"product_name": "마우스", "quantity": 1, "unit_price": 50000}],
        },
        headers={"X-Customer-Name": "미구독자"},
    )
    order_id = response.json()["id"]
    await asyncio.sleep(1)

    payment = await async_client.get(f"/api/v1/payments/order/{order_id}")
    assert payment.json()["applied_discount_type"] == "none"
    assert payment.json()["discount_amount"] == 0
```

```python
# tests/integration/test_shipping_with_subscription.py

async def test_premium_subscriber_free_shipping(async_client: AsyncClient):
    """Premium 구독자는 금액 무관하게 무료배송"""
    # Premium 구독 생성 + 소액 주문
    await async_client.post("/api/v1/subscriptions", json={
        "customer_name": "VIP", "tier": "premium",
    })
    response = await async_client.post(
        "/api/v1/orders",
        json={"customer_name": "VIP",
              "items": [{"product_name": "볼펜", "quantity": 1, "unit_price": 1000}]},
        headers={"X-Customer-Name": "VIP"},
    )
    order_id = response.json()["id"]
    await asyncio.sleep(1)

    shipment = await async_client.get(f"/api/v1/shipping/order/{order_id}")
    assert shipment.json()["shipping_fee"] == 0
    assert shipment.json()["fee_discount_type"] == "premium_free"
```

### 7.3 전체 Saga 테스트

```python
# tests/integration/test_full_saga.py

async def test_full_order_saga_with_basic_subscription(async_client: AsyncClient):
    """Basic 구독자의 주문 전체 흐름:
    구독 생성 → 주문 → 결제(5%할인) → 배송(50%할인) → Tracking 확인"""

    # 1. Basic 구독 생성
    await async_client.post("/api/v1/subscriptions", json={
        "customer_name": "김구독", "tier": "basic",
    })

    # 2. 40,000원 주문 (Basic: 배송비 무료 기준 30,000원 충족)
    response = await async_client.post(
        "/api/v1/orders",
        json={"customer_name": "김구독",
              "items": [{"product_name": "키보드", "quantity": 2, "unit_price": 20000}]},
        headers={"X-Customer-Name": "김구독"},
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    await asyncio.sleep(2)  # Saga 완료 대기

    # 3. Tracking 타임라인 확인
    tracking = await async_client.get(f"/api/v1/tracking/order/{order_id}/timeline")
    events = tracking.json()["events"]
    event_types = [e["event_type"] for e in events]

    assert "order.created" in event_types

    # 결제 승인된 경우 (90% 확률)
    if "payment.approved" in event_types:
        # 할인 확인: 40,000 * 5% = 2,000원 할인
        payment = await async_client.get(f"/api/v1/payments/order/{order_id}")
        assert payment.json()["discount_amount"] == 2000

        # 배송비 확인: 40,000원 > 30,000원이므로 Basic 무료배송
        shipment = await async_client.get(f"/api/v1/shipping/order/{order_id}")
        assert shipment.json()["shipping_fee"] == 0

        assert "shipment.created" in event_types
```

---

## 8. 구현 단계 (Phase)

### Phase 1: 뼈대 + Subscriptions + Orders 모듈

> 목표: Hexagonal 구조, DI, 기본 CRUD가 돌아가는 것 확인

- [ ] 프로젝트 셋업 (pyproject.toml, Docker Compose, PostgreSQL)
- [ ] `shared/` 모듈 (config, database, base_model, subscription_context)
- [ ] Subscriptions 모듈 전체 (도메인 → 인프라 → 프레젠테이션)
- [ ] Orders 도메인 레이어 (Entity, Value Object, Protocol)
- [ ] Orders 인프라 레이어 (SQLAlchemy Model, Repository)
- [ ] Orders 프레젠테이션 (Router, Schema)
- [ ] Dishka DI 연결
- [ ] Alembic 마이그레이션
- [ ] 단위 테스트: Order 엔티티, Money, 상태 전이, Subscription 엔티티

**체감 체크포인트:**
- `domain/` 에서 `grep -r "import sqlalchemy"` → 0건
- 단위 테스트가 DB 없이 0.1초 안에 끝남

### Phase 2: 이벤트 버스 + Payments 모듈 + 구독 할인 정책

> 목표: 모듈 간 이벤트 통신 + DI 정책 주입 체감

- [ ] InMemoryEventBus 구현
- [ ] 이벤트 정의 (shared/events.py)
- [ ] Orders → OrderCreatedEvent 발행
- [ ] Payments 도메인 (Entity, DiscountPolicy Protocol)
- [ ] 할인 정책 구현체 (SubscriptionDiscountPolicy, NoDiscountPolicy)
- [ ] FakePaymentGateway
- [ ] DI에서 SubscriptionContext → 할인 정책 자동 주입
- [ ] 단위 테스트: 할인 정책 (3가지 등급)
- [ ] 통합 테스트: Premium 구독자 주문 → 10% 할인 확인

**체감 체크포인트:**
- `orders/` 에서 `grep -r "import payments"` → 0건
- `payments/` 에서 `grep -r "import subscriptions"` → 0건
- DI 설정에서 tier만 바꾸면 할인율이 달라지는 것 확인
- FakeGateway 10% 거절 확인

### Phase 3: Shipping + 구독 배송비 정책

> 목표: 두 번째 정책 주입 + 구독이 여러 도메인에 영향을 주되 느슨한 것 체감

- [ ] Shipping 모듈 (도메인 + 인프라 + 프레젠테이션)
- [ ] 배송비 정책 구현체 (Standard, Basic, Premium)
- [ ] DI에서 SubscriptionContext → 배송비 정책 자동 주입
- [ ] PaymentApprovedEvent → 배송 자동 생성
- [ ] 단위 테스트: 배송비 정책 (3가지 등급 × 금액 조건)
- [ ] 통합 테스트: 구독 등급별 배송비 확인

**체감 체크포인트:**
- `shipping/` 에서 `grep -r "import subscriptions"` → 0건
- Premium 1,000원 주문 → 배송비 0원 확인
- Basic 40,000원 주문 → 배송비 0원 (3만원 이상), 20,000원 주문 → 배송비 1,500원

### Phase 4: Tracking 모듈 + 전체 Saga

> 목표: 모든 이벤트가 연결되고, 실패 보상 흐름까지 동작

- [ ] Tracking 모듈 (모든 이벤트 구독, 기록)
- [ ] Tracking 조회 API (타임라인)
- [ ] 보상 로직: PaymentRejectedEvent → Order CANCELLED
- [ ] SubscriptionActivated/Expired 이벤트도 Tracking에 기록
- [ ] 전체 Saga 통합 테스트 (성공 + 실패)
- [ ] E2E 테스트

**체감 체크포인트:**
- 주문 1개 생성 → Tracking에 모든 이벤트 타임라인 확인
- 결제 실패 → Order CANCELLED 자동 전환 확인
- 구독 활성화/만료도 Tracking에 기록 확인

### Phase 5: CQRS 고도화 + Observability

> 목표: Command/Query 분리 심화 + 로깅

- [ ] Command/Query 핸들러 정리
- [ ] 주문 목록 Query에 ReadModel 적용 (할인/배송비 요약 포함)
- [ ] 페이지네이션, 필터링
- [ ] structlog 로깅 미들웨어
- [ ] 에러 핸들링 표준화

### Phase 6: 프로덕션 배포

> 목표: Docker로 프로덕션 환경 구성

- [ ] Dockerfile (multi-stage build)
- [ ] docker-compose.yml (PostgreSQL + App)
- [ ] Gunicorn + Uvicorn workers 설정
- [ ] 환경별 설정 (dev / prod)
- [ ] Health check 엔드포인트

---

## 9. 핵심 설계 결정 요약

| 결정 | 선택 | 이유 |
|------|------|------|
| 모놀리스 vs MSA | **모듈러 모놀리스** | 학습 복잡도 관리, 이벤트 기반으로 MSA 전환 가능 |
| DB 공유 vs 분리 | **공유 (모듈별 테이블)** | 모놀리스이므로 1개 DB |
| 이벤트 버스 | **인메모리** | 학습용, Protocol로 Kafka 교체 가능 |
| DI | **Dishka** | 스코프 관리, 정책 주입 체감 |
| 구독 → 다른 모듈 영향 | **SubscriptionContext DTO + DI 정책 주입** | 모듈 간 직접 의존 없이 정책만 교체 |
| CQRS 수준 | **핸들러 분리** | 별도 DB까지는 오버 |
| 결제 | **Fake Gateway** | 정책 패턴에 집중 |
| 인증 | **X-Customer-Name 헤더** | 아키텍처 학습에 집중 |

---

## 10. 참고: 나중에 확장 가능한 방향

- `InMemoryEventBus` → **Redis Pub/Sub** 또는 **Kafka** (도메인 코드 변경 0)
- `FakePaymentGateway` → **실제 PG 연동** (Protocol 교체)
- `SubscriptionContext` → 외부 구독 관리 서비스 연동
- 쿠폰 할인 정책 추가 (DiscountPolicy 구현체 추가 + DI 등록만)
- JWT 인증 + RBAC
- 모듈 → 별도 서비스 분리 (진짜 MSA 전환)

---