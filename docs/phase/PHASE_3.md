# Phase 3: Shipping 모듈 + 구독 배송비 정책

> **목표**: 두 번째 정책 주입을 통해 구독이 여러 도메인에 영향을 주되 느슨한 것을 체감한다.

---

## 3.1 Shipping 모듈 구현

### 레이어 구조

```
shipping/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   ├── policies.py          # ★ 배송비 정책 구현체
│   ├── exceptions.py
│   └── interfaces.py        # ★ ShippingFeePolicy Protocol
├── application/
│   ├── commands.py
│   ├── command_handlers.py
│   └── event_handlers.py    # PaymentApprovedEvent 수신
├── infrastructure/
│   ├── models.py
│   ├── mappers.py
│   └── repository.py
└── presentation/
    ├── schemas.py
    └── router.py
```

### domain/interfaces.py

```
핵심:
  ShippingFeePolicy(Protocol):
    - calculate_fee(order_amount: Money) → ShippingFeeResult
  ShippingFeeResult(@dataclass, frozen):
    - fee: Money              # 실제 배송비
    - original_fee: Money     # 할인 전 기본 배송비
    - discount_type: str      # "none", "basic_half", "premium_free"
    - reason: str             # 사람이 읽을 수 있는 사유
  ShipmentRepositoryProtocol(Protocol):
    - save, find_by_id, find_by_order_id, update
```

### domain/policies.py

```
핵심:
  BASE_SHIPPING_FEE = Money(Decimal("3000"))
  
  StandardShippingFeePolicy (미구독):
    - 기본 3,000원
    - 50,000원 이상 무료배송
  BasicShippingFeePolicy (Basic 구독):
    - 50% 할인 → 1,500원
    - 30,000원 이상 무료배송
  PremiumShippingFeePolicy (Premium 구독):
    - 항상 무료
  
  ★ Shipping은 "왜 무료인지" 모름. 주입된 Policy가 결정.
```

### domain/entities.py

```
핵심:
  Address: street, city, zip_code (Value Object)
  ShipmentStatus(str, Enum): PREPARING, IN_TRANSIT, DELIVERED
  Shipment:
    - id, order_id, status, address, shipping_fee(Money), original_fee(Money),
      fee_discount_type, tracking_number, estimated_delivery
    - create() 팩토리: PREPARING 상태
    - mark_in_transit(tracking_number)
    - mark_delivered()
    - 상태 전이: PREPARING → IN_TRANSIT → DELIVERED
```

### application/event_handlers.py

```
핵심:
  handle_payment_approved(event: PaymentApprovedEvent):
    - ShippingFeePolicy로 배송비 계산
    - Shipment.create()
    - repo.save()
    - event_bus.publish(ShipmentCreatedEvent)
  ★ PaymentApprovedEvent만 사용. Payments 모듈 import 없음.
```

### application/commands.py, command_handlers.py

```
핵심:
  UpdateShipmentStatusCommand(shipment_id, new_status):
    - 배송 시뮬레이션용 수동 상태 변경
  UpdateShipmentStatusHandler:
    - shipment.mark_in_transit() 또는 mark_delivered()
    - event_bus.publish(ShipmentStatusChangedEvent)
```

### presentation/router.py

```
엔드포인트:
  GET  /api/v1/shipping/{shipment_id}              → 배송 상세 (배송비 내역 포함)
  GET  /api/v1/shipping/order/{order_id}            → 주문별 배송 조회
  POST /api/v1/shipping/{shipment_id}/update-status → 배송 상태 변경 (시뮬레이션)
```

---

## 3.2 DI 컨테이너 확장

### `shared/di_container.py` 수정

```
추가:
  ShippingProvider:
    - Scope.REQUEST: shipping_fee_policy(sub_ctx: SubscriptionContext):
        match sub_ctx.tier:
          "premium" → PremiumShippingFeePolicy()
          "basic"   → BasicShippingFeePolicy()
          _         → StandardShippingFeePolicy()
    - Scope.REQUEST: shipment_repository, create_shipment_handler, update_status_handler
```

---

## 3.3 이벤트 핸들러 등록 확장

### `main.py` 수정

```
register_event_handlers 추가:
  - PaymentApprovedEvent → shipping의 handle_payment_approved
  - ShipmentCreatedEvent → orders의 handle_shipment_created (order.mark_shipping)
  - ShipmentStatusChangedEvent → orders의 handle_shipment_delivered (DELIVERED일 때 order.mark_delivered)
```

---

## 3.4 Orders 이벤트 핸들러 확장

### `orders/application/event_handlers.py` 수정

```
추가:
  handle_shipment_created(event: ShipmentCreatedEvent):
    - order.mark_shipping()
    - repo.update()
  handle_shipment_delivered(event: ShipmentStatusChangedEvent):
    - if event.new_status == "delivered":
      - order.mark_delivered()
      - repo.update()
```

---

## 3.5 테스트

### tests/unit/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_shipping_fee_policies.py` | Standard: 3,000원, 5만원↑ 무료. Basic: 1,500원, 3만원↑ 무료. Premium: 항상 무료. discount_type 확인. |
| `test_shipment_entity.py` | create → PREPARING, mark_in_transit → IN_TRANSIT, mark_delivered → DELIVERED, 잘못된 전이 |

### tests/integration/ 추가

| 파일 | 테스트 내용 |
|------|------------|
| `test_shipping_flow.py` | 결제 승인 → 배송 자동 생성 확인, 배송 상태 변경 시뮬레이션 |
| `test_shipping_with_subscription.py` | Premium 1,000원 주문 → 배송비 0원, Basic 40,000원 → 무료(3만↑), Basic 20,000원 → 1,500원, 미구독 30,000원 → 3,000원, 미구독 50,000원 → 무료 |

---

## 3.6 Phase 3 체감 체크포인트

```bash
# 1. Shipping에서 Subscriptions import 0건
grep -rn "from.*subscriptions\|import subscriptions" src/app/shipping/

# 2. Shipping에서 Payments import 0건
grep -rn "from.*payments\|import payments" src/app/shipping/

# 3. 구독 등급별 배송비 정책 확인
pytest tests/unit/test_shipping_fee_policies.py -v

# 4. Premium 1,000원 주문 → 배송비 0원 확인
pytest tests/integration/test_shipping_with_subscription.py -v

# 5. 전체 흐름: 주문 생성 → 결제 → 배송 자동 생성
pytest tests/integration/test_shipping_flow.py -v
```

---

## 3.7 Phase 3 완료 기준

- [ ] Shipping 모듈 13파일 구현
- [ ] 배송비 정책 3가지 구현 (Standard, Basic, Premium)
- [ ] DI에 ShippingProvider 추가
- [ ] 이벤트 핸들러 등록 확장 (PaymentApproved → Shipment 생성)
- [ ] Orders 이벤트 핸들러 확장 (ShipmentCreated/Delivered → 상태 변경)
- [ ] 단위 테스트 추가 (배송비 정책, Shipment 엔티티)
- [ ] 통합 테스트 추가 (구독별 배송비, 전체 흐름)
- [ ] 5개 체감 체크포인트 전부 통과