# Phase 2: 이벤트 버스 + Payments 모듈 + 구독 할인 정책

> **목표**: 모듈 간 import 없이 이벤트로 통신하는 것,
> DI가 구독 등급에 따라 할인 정책을 자동 주입하는 것을 체감한다.

---

## 2.1 이벤트 핸들러 등록 시스템

### `main.py` 수정

```
변경 내용:
  - lifespan에서 이벤트 핸들러 등록 함수 호출
  - register_event_handlers(event_bus, container) 함수 추가
  
구현:
  async def lifespan(app):
      container = app.state.dishka_container
      event_bus = await container.get(EventBus)  # APP 스코프
      register_event_handlers(event_bus, container)
      yield
      await container.close()
  
  register_event_handlers:
    - OrderCreatedEvent → payments의 handle_order_created
    - PaymentApprovedEvent → orders의 handle_payment_approved
    - PaymentRejectedEvent → orders의 handle_payment_rejected
    
  ★ 이벤트 핸들러 안에서 Dishka REQUEST 스코프를 수동 생성하여 의존성 주입
  ★ 이 등록 로직만이 "어떤 이벤트가 어떤 핸들러로 가는지" 아는 유일한 장소
```

### 이벤트 핸들러의 DI 스코프 처리

```
문제: 이벤트 핸들러는 HTTP 요청 바깥에서 실행됨 → Dishka REQUEST 스코프가 자동으로 열리지 않음
해결: 핸들러 내부에서 container의 REQUEST 스코프를 수동으로 열고 닫음

패턴:
  async def handle_order_created(event: OrderCreatedEvent):
      async with container() as request_container:
          handler = await request_container.get(ProcessPaymentHandler)
          await handler.handle(...)
```

---

## 2.2 Payments 모듈 구현

### 레이어 구조

```
payments/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   ├── policies.py          # ★ 할인 정책 구현체
│   ├── exceptions.py
│   └── interfaces.py        # ★ DiscountPolicy, PaymentGatewayProtocol
├── application/
│   ├── commands.py
│   ├── command_handlers.py
│   └── event_handlers.py    # OrderCreatedEvent 수신
├── infrastructure/
│   ├── models.py
│   ├── mappers.py
│   ├── repository.py
│   └── fake_gateway.py      # ★ 90% 승인 Fake PG
└── presentation/
    ├── schemas.py
    └── router.py
```

### domain/interfaces.py

```
역할: 결제 도메인의 Port 정의
핵심:
  DiscountPolicy(Protocol):
    - calculate_discount(amount: Money) → DiscountResult
  DiscountResult(@dataclass, frozen):
    - discount_amount: Money
    - discount_type: str  ("none", "basic_subscription", "premium_subscription")
  PaymentGatewayProtocol(Protocol):
    - process(payment: Payment) → GatewayResult
  GatewayResult(@dataclass, frozen):
    - success: bool
    - transaction_id: str | None
    - message: str
  PaymentValidationPolicy(Protocol):
    - validate(method: PaymentMethod, amount: Money) → None  (실패 시 예외)
  PaymentRepositoryProtocol(Protocol):
    - save, find_by_id, find_by_order_id
  
  ★ Payments 도메인은 "할인이 왜 5%인지" 모른다. Protocol만 알 뿐.
```

### domain/entities.py

```
역할: Payment 엔티티
핵심:
  PaymentMethod(str, Enum): CREDIT_CARD, BANK_TRANSFER, VIRTUAL_ACCOUNT
  PaymentStatus(str, Enum): PENDING, APPROVED, REJECTED
  Payment:
    - id, order_id, original_amount(Money), discount_amount(Money), final_amount(Money)
    - method, status, applied_discount_type, processed_at
    - create() 팩토리: PENDING 상태로 시작
    - approve(transaction_id): PENDING → APPROVED
    - reject(reason): PENDING → REJECTED
```

### domain/value_objects.py

```
역할: Money를 orders에서 재사용할지 별도 정의할지 결정
선택: shared/에 공통 Money를 두거나, orders의 Money를 그대로 사용
  → orders/domain/value_objects.py의 Money를 payments에서도 import
  → 단, 이는 "모듈 간 import 금지" 원칙에 위배됨
  → ★ 해결: Money를 shared/value_objects.py로 승격
  → Phase 2 시작 시 리팩토링 포함
```

### domain/policies.py

```
역할: DiscountPolicy 구현체들
핵심:
  SubscriptionDiscountPolicy:
    - __init__(rate: Decimal, discount_type: str)
    - calculate_discount(amount): amount.apply_rate(rate) → DiscountResult
    - ★ 이 클래스는 "구독" 단어를 알지만 Subscription 모듈을 import하지 않음
    - ★ rate와 discount_type은 DI가 주입
  NoDiscountPolicy:
    - calculate_discount(amount): 항상 0원, discount_type="none"
```

### domain/exceptions.py

```
역할: 결제 도메인 예외
핵심:
  - PaymentError (base)
  - PaymentNotFoundError
  - PaymentValidationError(reason) — 한도 초과 등
  - PaymentGatewayError — 게이트웨이 통신 실패
```

### application/commands.py

```
역할: Command DTO
핵심:
  ProcessPaymentCommand:
    - order_id, amount(Decimal), customer_name, method(str)
```

### application/command_handlers.py

```
역할: 결제 처리 핸들러
핵심:
  ProcessPaymentHandler:
    - 의존성: PaymentRepositoryProtocol, PaymentGatewayProtocol,
              DiscountPolicy, PaymentValidationPolicy, EventBus
    - handle(command):
      1. validation_policy.validate(method, amount) — 한도 체크
      2. discount = discount_policy.calculate_discount(amount) — ★ 정책 적용
      3. final_amount = amount - discount_amount
      4. Payment.create(order_id, amount, discount, final_amount, method)
      5. gateway_result = await gateway.process(payment) — Fake PG 호출
      6-a. 승인 시: payment.approve(), publish(PaymentApprovedEvent)
      6-b. 거절 시: payment.reject(), publish(PaymentRejectedEvent)
      7. repo.save(payment)
  
  ★ 핸들러는 어떤 DiscountPolicy가 주입되는지 모른다
  ★ VIP든 일반이든 동일한 코드가 실행됨 — 이것이 정책 주입의 핵심
```

### application/event_handlers.py

```
역할: OrderCreatedEvent 수신 → 결제 자동 시작
핵심:
  handle_order_created(event: OrderCreatedEvent):
    - ProcessPaymentCommand 생성
    - ProcessPaymentHandler.handle() 호출
    - ★ Orders 모듈을 import하지 않음. event의 데이터만 사용.
```

### infrastructure/fake_gateway.py

```
역할: 90% 승인 / 10% 거절 Fake PG
핵심:
  FakePaymentGateway:
    - process(payment):
      - asyncio.sleep(0.3) — 네트워크 지연 시뮬레이션
      - random.random() < 0.9 → 승인
      - else → 거절 ("Insufficient funds")
  ★ PaymentGatewayProtocol 구현 → DI에서 교체 가능
```

### infrastructure/models.py, mappers.py, repository.py

```
역할: Orders와 동일 패턴
핵심:
  PaymentModel: id, order_id, original_amount, discount_amount, final_amount,
                method, status, applied_discount_type, processed_at
  find_by_order_id: 주문별 결제 조회
```

### presentation/schemas.py, router.py

```
역할: API 인터페이스
핵심:
  엔드포인트 (읽기 전용 — 결제 생성은 이벤트가 처리):
    GET /api/v1/payments/{payment_id}       → 결제 상세 (할인 내역 포함)
    GET /api/v1/payments/order/{order_id}   → 주문별 결제 조회
  PaymentResponse에 포함:
    - original_amount, discount_amount, final_amount
    - applied_discount_type ("none" / "basic_subscription" / "premium_subscription")
```

---

## 2.3 DI 컨테이너 확장

### `shared/di_container.py` 수정

```
추가:
  SubscriptionContextProvider (기존 SubscriptionsProvider에 추가 또는 별도):
    - Scope.REQUEST: subscription_context
    - customer_name을 Request 헤더(X-Customer-Name)에서 추출
    - repo.find_active_by_customer() → SubscriptionContext 생성
    - 활성 구독 없으면 SubscriptionContext.guest() 반환
  
  PaymentsProvider:
    - Scope.REQUEST: payment_gateway → FakePaymentGateway()
    - Scope.REQUEST: discount_policy(sub_ctx: SubscriptionContext):
        match sub_ctx.tier:
          "premium" → SubscriptionDiscountPolicy(rate=0.10, type="premium_subscription")
          "basic"   → SubscriptionDiscountPolicy(rate=0.05, type="basic_subscription")
          _         → NoDiscountPolicy()
    - Scope.REQUEST: validation_policy → StandardPaymentValidationPolicy()
    - Scope.REQUEST: payment_repository, process_payment_handler
  
  ★ 이 match 문이 "구독 등급 → 할인율" 매핑의 유일한 장소
  ★ Payments 모듈 코드는 여기에 의존하지 않음
```

---

## 2.4 Money 리팩토링

```
변경: orders/domain/value_objects.py의 Money를 shared/value_objects.py로 이동
이유: Payments, Shipping에서도 동일한 Money가 필요하지만 모듈 간 import 금지
방법:
  1. shared/value_objects.py 생성 (Money 클래스)
  2. orders/domain/value_objects.py에서 Money 제거, OrderStatus만 남김
  3. orders의 모든 Money import를 shared.value_objects로 변경
  4. payments에서도 shared.value_objects.Money 사용
```

---

## 2.5 Orders 이벤트 핸들러 구현

### `orders/application/event_handlers.py`

```
역할: 결제 결과를 수신하여 주문 상태 변경
핵심:
  handle_payment_approved(event: PaymentApprovedEvent):
    - repo.find_by_id(event.order_id)
    - order.mark_paid()
    - repo.update(order)
  handle_payment_rejected(event: PaymentRejectedEvent):
    - repo.find_by_id(event.order_id)
    - order.cancel()
    - repo.update(order)
  ★ Orders는 Payments를 import하지 않음. event 데이터만 사용.
```

---

## 2.6 테스트

### tests/unit/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_discount_policies.py` | Premium 10% 할인, Basic 5% 할인, NoDiscount 0원, discount_type 확인 |
| `test_payment_entity.py` | Payment.create → PENDING, approve → APPROVED, reject → REJECTED, 상태 전이 검증 |

### tests/integration/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_payment_flow.py` | 주문 생성 → 이벤트 → 결제 자동 생성 확인, 결제 상세 조회 |
| `test_payment_with_subscription.py` | Premium 구독자 주문 → 10% 할인 확인, Basic 구독자 → 5% 확인, 미구독자 → 할인 0 확인, 결제 거절 → 주문 CANCELLED 확인 |

---

## 2.7 Phase 2 체감 체크포인트

```bash
# 1. Orders에서 Payments import 0건
grep -rn "from.*payments\|import payments" src/app/orders/

# 2. Payments에서 Subscriptions import 0건
grep -rn "from.*subscriptions\|import subscriptions" src/app/payments/

# 3. DI 설정만 바꾸면 할인 정책이 교체됨
# → di_container.py의 match 문에서 rate 값만 변경하면 됨

# 4. FakeGateway 10% 거절 확인
# → 통합 테스트에서 여러 번 실행 시 간헐적 거절 발생

# 5. 전체 테스트 통과
pytest tests/ -v
```

---

## 2.8 Phase 2 완료 기준

- [ ] Money를 shared/value_objects.py로 리팩토링
- [ ] Payments 모듈 13파일 구현
- [ ] 이벤트 핸들러 등록 시스템 구현 (main.py)
- [ ] Orders 이벤트 핸들러 구현 (payment_approved/rejected)
- [ ] DI에 PaymentsProvider 추가 (구독 기반 할인 정책 주입)
- [ ] 단위 테스트 추가 (할인 정책, Payment 엔티티)
- [ ] 통합 테스트 추가 (주문→결제 이벤트 흐름, 구독별 할인 검증)
- [ ] 5개 체감 체크포인트 전부 통과