# Phase 4: Tracking 모듈 (Saga)

> **목표**: 모든 이벤트가 하나의 타임라인으로 기록되는 것,
> 실패 시 보상 트랜잭션이 동작하는 것을 체감한다.

---

## 4.1 Tracking 모듈 구현

### 레이어 구조

```
tracking/
├── domain/
│   ├── entities.py
│   ├── exceptions.py
│   └── interfaces.py
├── application/
│   ├── queries.py
│   ├── query_handlers.py
│   └── event_handlers.py    # ★ 모든 이벤트를 구독
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
핵심:
  TrackingPhase(str, Enum):
    - ORDER_PLACED, PAYMENT_PROCESSING, PAYMENT_COMPLETED, SHIPPING, DELIVERED, FAILED
  TrackingEvent:
    - event_type: str ("order.created", "payment.approved", ...)
    - timestamp: datetime
    - module: str ("orders", "payments", "shipping", "subscriptions")
    - detail: dict (이벤트 페이로드 요약)
  OrderTracking:
    - id, order_id, customer_name, subscription_tier (스냅샷)
    - events: list[TrackingEvent]
    - current_phase: TrackingPhase
    - started_at, completed_at
    - add_event(event_type, module, detail): events에 추가 + phase 업데이트
    - mark_failed(reason): phase → FAILED
    - mark_completed(): phase → DELIVERED, completed_at 설정
```

### application/event_handlers.py

```
역할: ★ 모든 도메인 이벤트를 구독하여 기록
핵심:
  handle_order_created(event):
    - OrderTracking 생성 (ORDER_PLACED)
    - add_event("order.created", "orders", {amount, items_count})
  handle_payment_approved(event):
    - tracking.add_event("payment.approved", "payments", {final_amount, discount_type})
    - phase → PAYMENT_COMPLETED
  handle_payment_rejected(event):
    - tracking.add_event("payment.rejected", "payments", {reason})
    - tracking.mark_failed(reason)
  handle_shipment_created(event):
    - tracking.add_event("shipment.created", "shipping", {shipping_fee, discount_type})
    - phase → SHIPPING
  handle_shipment_status_changed(event):
    - tracking.add_event("shipment.{status}", "shipping", {})
    - if DELIVERED: tracking.mark_completed()
  handle_subscription_activated(event):
    - tracking에 해당 customer의 미완료 추적이 있으면 구독 정보 업데이트
    - 별도 기록: "subscription.activated"
  
  ★ Tracking은 읽기 + 기록 전용. 다른 모듈에 이벤트를 발행하지 않음.
  ★ 모든 모듈의 이벤트를 구독하지만, 어떤 모듈도 import하지 않음.
```

### application/queries.py, query_handlers.py

```
핵심:
  GetOrderTrackingQuery(order_id):
    - 주문의 전체 추적 정보 반환
  GetOrderTimelineQuery(order_id):
    - events만 시간순으로 반환 (타임라인 형태)
```

### presentation/router.py

```
엔드포인트:
  GET /api/v1/tracking/order/{order_id}           → 전체 추적 정보
  GET /api/v1/tracking/order/{order_id}/timeline   → 타임라인 (이벤트 목록)
  
  TrackingResponse:
    - order_id, customer_name, subscription_tier, current_phase
    - events: [{event_type, timestamp, module, detail}, ...]
    - started_at, completed_at
```

---

## 4.2 이벤트 핸들러 등록 확장

### `main.py` 수정

```
register_event_handlers 추가:
  - OrderCreatedEvent → tracking handler
  - PaymentApprovedEvent → tracking handler
  - PaymentRejectedEvent → tracking handler
  - ShipmentCreatedEvent → tracking handler
  - ShipmentStatusChangedEvent → tracking handler
  - SubscriptionActivatedEvent → tracking handler
  - SubscriptionExpiredEvent → tracking handler
  
  ★ 하나의 이벤트에 여러 핸들러 등록 가능
  예: PaymentApprovedEvent → [orders handler, shipping handler, tracking handler]
```

---

## 4.3 DI 컨테이너 확장

```
추가:
  TrackingProvider:
    - tracking_repository
    - query handlers
    - ★ event_handlers는 DI 아닌 수동 등록 (이벤트 핸들러 패턴)
```

---

## 4.4 인프라 (models.py)

```
핵심:
  OrderTrackingModel:
    - id, order_id(unique, indexed), customer_name, subscription_tier
    - current_phase, started_at, completed_at
  TrackingEventModel:
    - id, tracking_id(FK), event_type, timestamp, module, detail(JSON)
  
  detail 컬럼은 JSON 타입 (PostgreSQL JSONB, SQLite TEXT)
```

---

## 4.5 테스트

### tests/unit/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_tracking_entity.py` | OrderTracking 생성 → ORDER_PLACED, add_event 후 events 확인, mark_failed → FAILED, mark_completed → DELIVERED + completed_at 설정 |

### tests/integration/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_full_saga.py` | 전체 성공 흐름: 주문→결제→배송→delivered → tracking에 모든 이벤트 기록 확인, 타임라인 순서 검증 |
| `test_saga_failure.py` | 결제 거절 시: tracking에 order.created + payment.rejected 기록, phase=FAILED, 주문 CANCELLED 확인 |

---

## 4.6 Phase 4 체감 체크포인트

```bash
# 1. Tracking에서 다른 모듈 import 0건
grep -rn "from.*orders\|from.*payments\|from.*shipping\|from.*subscriptions" src/app/tracking/
# shared만 있으면 OK

# 2. 주문 1개 → 타임라인에 전체 이벤트 기록
pytest tests/integration/test_full_saga.py -v

# 3. 결제 실패 → FAILED + 주문 CANCELLED 자동 전환
pytest tests/integration/test_saga_failure.py -v

# 4. 전체 테스트
pytest tests/ -v
```

---

## 4.7 Phase 4 완료 기준

- [ ] Tracking 모듈 11파일 구현
- [ ] 모든 도메인 이벤트에 대한 핸들러 등록
- [ ] 타임라인 조회 API
- [ ] 보상 로직 (결제 실패 → 주문 취소) 동작 확인
- [ ] 전체 Saga 통합 테스트 (성공 + 실패)
- [ ] 4개 체감 체크포인트 전부 통과