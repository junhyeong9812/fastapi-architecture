# Phase 5: CQRS 고도화 + Observability

> **목표**: Command/Query 분리의 실제 이점을 체감하고,
> structlog 기반 구조화된 로깅으로 운영 가시성을 확보한다.

---

## 5.1 CQRS 고도화

### 주문 목록 ReadModel

```
현재: list_orders가 Order 엔티티 전체를 반환 → 오버페칭
변경: 목록 조회용 경량 DTO(ReadModel) 도입

OrderSummary:
  - id, customer_name, status, total_amount
  - discount_amount, shipping_fee, final_amount  ← 다른 모듈 데이터 조인
  - created_at
  
구현:
  OrderReadRepository에 list_order_summaries() 추가
  → orders + payments + shipping 테이블 조인 쿼리
  → ★ ReadModel은 여러 모듈의 데이터를 합칠 수 있음 (읽기 최적화)
  → ★ Command 측은 변경 없음 — 이것이 CQRS 분리의 이점
```

### Tracking ReadModel

```
현재: Tracking 조회가 모든 events를 반환
변경: 요약 정보 포함
  - total_duration (시작~완료 소요 시간)
  - step_count (이벤트 수)
  - 최신 이벤트 하이라이트
```

---

## 5.2 에러 핸들링 표준화

### 글로벌 예외 핸들러

```
app/shared/exception_handlers.py:
  - OrderNotFoundError → 404
  - InvalidOrderError → 400
  - InvalidStatusTransition → 400 (conflict)
  - PaymentNotFoundError → 404
  - PaymentValidationError → 422
  - SubscriptionNotFoundError → 404
  - InvalidSubscriptionError → 400
  - ShipmentNotFoundError → 404
  - 기타 예외 → 500 (로깅 포함)
  
표준 에러 응답:
  {"error": {"code": "ORDER_NOT_FOUND", "message": "...", "detail": {}}}
```

### 각 router에서 try-except 제거

```
변경: 개별 router의 try-except를 제거하고 글로벌 핸들러에 위임
이유: 중복 제거 + 일관된 에러 형식
```

---

## 5.3 structlog 로깅 강화

### 요청 컨텍스트

```
미들웨어에서 request_id를 생성하여 structlog context에 바인딩
→ 하나의 요청에서 발생한 모든 로그에 동일한 request_id 포함
→ 이벤트 핸들러 체인도 추적 가능
```

### 이벤트 흐름 로깅

```
event_bus.publish() 시:
  - event_name, handler_count, request_id
  - 각 handler 실행 시: handler_name, duration_ms, success/failure
→ 주문 하나의 전체 이벤트 흐름을 로그로 추적 가능
```

### 프로덕션 로깅 설정

```
dev: ConsoleRenderer (컬러)
prod: JSONRenderer (구조화 JSON)
→ config.ENV에 따라 분기
```

---

## 5.4 페이지네이션 + 필터링

### 공통 페이지네이션 스키마

```
shared/pagination.py:
  PaginatedRequest(page=1, size=20, sort_by, sort_order)
  PaginatedResponse(items, total, page, size, total_pages)
```

### 주문 필터

```
ListOrdersQuery 확장:
  - customer_name
  - status
  - min_amount / max_amount
  - created_after / created_before
  - sort_by (created_at / total_amount)
```

---

## 5.5 테스트

| 파일 | 테스트 내용 |
|------|------------|
| `test_order_read_model.py` | OrderSummary에 할인/배송비 포함 확인 |
| `test_error_handling.py` | 각 예외에 대해 올바른 HTTP 상태 + 표준 에러 형식 확인 |
| `test_pagination.py` | 페이지네이션, 필터링, 정렬 |

---

## 5.6 Phase 5 완료 기준

- [ ] 주문 목록 ReadModel (조인 쿼리)
- [ ] 글로벌 예외 핸들러 + 표준 에러 응답
- [ ] structlog 요청 컨텍스트 (request_id)
- [ ] 페이지네이션 공통화
- [ ] 필터링 확장
- [ ] 테스트 추가