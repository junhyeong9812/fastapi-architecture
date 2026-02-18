# 🛒 ShopTracker

> FastAPI 클린 아키텍처 학습을 위한 모듈러 모놀리스 프로젝트

주문 → 결제 → 배송 흐름을 **Hexagonal Architecture**로 구현하며,
모듈 간 통신은 **이벤트 버스**, 정책 교체는 **DI**로 처리합니다.

---

## 무엇을 배우는 프로젝트인가

| 패턴 | 어디서 체감하는가 |
|------|------------------|
| Hexagonal Architecture | `domain/`에 FastAPI·SQLAlchemy import 0건 |
| 의존성 역전 (DIP) | Repository를 Protocol로 정의, 구현체 교체 |
| DI + 정책 주입 | 구독 등급에 따라 할인·배송비 정책이 자동 교체 |
| 내부 이벤트 버스 | 모듈 간 직접 import 없이 이벤트로만 소통 |
| CQRS | Command(주문 생성)와 Query(목록 조회)의 핸들러 분리 |
| Saga / 추적 | 주문→결제→배송 전체 여정을 Tracking 모듈이 기록 |
| 테스트 전략 | 도메인 단위 테스트(DB 없음) + 통합 테스트 + E2E |

---

## 아키텍처

```
┌─────────────────────────────────────────────┐
│               ShopTracker App               │
│                                             │
│  ┌────────┐ ┌─────────┐ ┌────────┐        │
│  │ Orders │ │Payments │ │Shipping│        │
│  └───┬────┘ └────┬────┘ └───┬────┘        │
│      │      ┌────┴────┐     │              │
│      │      │Subscribe│     │              │
│      │      └────┬────┘     │              │
│      └───────────┼──────────┘              │
│           ┌──────┴──────┐                  │
│           │  Tracking   │                  │
│           └──────┬──────┘                  │
│           ┌──────┴──────┐                  │
│           │  Event Bus  │                  │
│           └─────────────┘                  │
└─────────────────────────────────────────────┘
```

**모듈 간 규칙**: 직접 import 금지. 이벤트 버스를 통해서만 소통.

### 모듈별 역할

| 모듈 | 역할 |
|------|------|
| **Orders** | 주문 생성·취소, 상태 전이 관리 |
| **Payments** | 결제 처리, 구독 기반 할인 정책 적용, Fake PG |
| **Shipping** | 배송 생성·상태 관리, 구독 기반 배송비 정책 적용 |
| **Subscriptions** | 구독 등급 관리 (NONE / BASIC / PREMIUM) |
| **Tracking** | 모든 이벤트를 구독하여 주문 여정(Saga) 기록 |

### 구독 등급별 혜택

| 혜택 | NONE | BASIC | PREMIUM |
|------|:----:|:-----:|:-------:|
| 결제 할인 | 0% | 5% | 10% |
| 배송비 | 3,000원 | 50% 할인 | 무료 |
| 무료배송 기준 | 5만원↑ | 3만원↑ | 항상 |

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Framework | FastAPI 0.129+ |
| Python | 3.12 |
| DB | PostgreSQL 16 + asyncpg |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| DI | Dishka |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Testing | pytest + httpx AsyncClient |
| Logging | structlog |
| Container | Docker Compose |
| ASGI | Gunicorn + Uvicorn workers |

---

## 프로젝트 구조

```
src/app/
├── main.py                  # FastAPI 앱 + lifespan
├── shared/                  # 모듈 간 공유
│   ├── config.py
│   ├── database.py
│   ├── event_bus.py
│   ├── events.py
│   ├── subscription_context.py
│   └── di_container.py
├── orders/                  # 📦 주문
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── presentation/
├── payments/                # 💳 결제
│   ├── domain/              # policies.py ← 할인 정책
│   ├── application/
│   ├── infrastructure/      # fake_gateway.py
│   └── presentation/
├── shipping/                # 🚚 배송
│   ├── domain/              # policies.py ← 배송비 정책
│   ├── application/
│   ├── infrastructure/
│   └── presentation/
├── subscriptions/           # 🎫 구독
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── presentation/
└── tracking/                # 📊 추적
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/
```

각 모듈은 Hexagonal Architecture를 따릅니다:
- **domain/** — 순수 Python. 외부 프레임워크 의존 없음.
- **application/** — Use Case (Command/Query 핸들러)
- **infrastructure/** — SQLAlchemy, 외부 서비스 연동
- **presentation/** — FastAPI Router, Pydantic Schema

---

## 시작하기

### 요구사항

- Python 3.12+
- Docker & Docker Compose

### 실행

```bash
# 저장소 클론
git clone <repo-url>
cd shoptracker

# 컨테이너 실행 (PostgreSQL + App)
docker compose up -d

# 마이그레이션
docker compose exec app alembic upgrade head

# API 문서 확인
open http://localhost:8000/docs
```

### 개발 환경

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -e ".[dev]"

# DB 실행 (PostgreSQL만)
docker compose up -d db

# 개발 서버
uvicorn src.app.main:app --reload

# 테스트
pytest                          # 전체
pytest tests/unit               # 단위 테스트만 (DB 불필요)
pytest tests/integration        # 통합 테스트 (DB 필요)
```

---

## 이벤트 흐름

```
주문 생성 ──▶ OrderCreatedEvent
                  │
            ┌─────┼──────────┐
            ▼     ▼          ▼
        Payments  Tracking   (기록)
            │
    ┌───────┴───────┐
    ▼               ▼
 Approved        Rejected
    │               │
 ┌──┴──┐        ┌──┴──┐
 ▼     ▼        ▼     ▼
Ship  Track   Cancel  Track
```

결제·배송 생성은 API가 아닌 **이벤트 핸들러**가 자동 처리합니다.

---

## API 요약

| 모듈 | Endpoint | 주요 기능 |
|------|----------|-----------|
| Subscriptions | `POST /api/v1/subscriptions` | 구독 생성 |
| Orders | `POST /api/v1/orders` | 주문 생성 |
| Orders | `GET /api/v1/orders` | 주문 목록 |
| Payments | `GET /api/v1/payments/order/{id}` | 결제 상세 (할인 내역) |
| Shipping | `GET /api/v1/shipping/order/{id}` | 배송 상세 (배송비 내역) |
| Tracking | `GET /api/v1/tracking/order/{id}/timeline` | 주문 여정 타임라인 |

전체 API 명세는 `/docs` (Swagger UI)에서 확인할 수 있습니다.

---

## 테스트

```bash
pytest tests/unit                       # 도메인 로직 (DB 없음, <1초)
pytest tests/integration                # 이벤트 + DB 연동
pytest tests/e2e                        # API 엔드포인트
pytest --cov=src/app --cov-report=html  # 커버리지
```

단위 테스트는 DB, FastAPI, 외부 서비스 없이 순수 도메인 로직만 검증합니다.
이것이 Hexagonal Architecture의 핵심 이점입니다.

---

## 설계 문서

상세 설계 (도메인 엔티티, 이벤트 정의, DI 구조, 정책 객체, 구현 Phase 등)는
[ShopTracker_Design_Document_v2.md](./docs/ShopTracker_Design_Document_v2.md)를 참고하세요.

---

## License

MIT