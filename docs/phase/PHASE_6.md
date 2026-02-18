# Phase 6: 프로덕션 배포

> **목표**: Docker Compose로 프로덕션 환경을 구성하고,
> Gunicorn + Uvicorn workers 구조를 체감한다.

---

## 6.1 Dockerfile (Multi-stage Build)

```
# Stage 1: Builder
FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
EXPOSE 8000
CMD ["gunicorn", "src.app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", ...]
```

```
핵심:
  - multi-stage로 빌드 의존성 제거 → 이미지 크기 축소
  - gunicorn -w 4: worker 4개 (CPU 코어 수 × 2 권장)
  - uvicorn.workers.UvicornWorker: async 지원 worker class
```

---

## 6.2 docker-compose.yml (프로덕션)

```
services:
  db:
    image: postgres:16-alpine
    environment: (user, password, db)
    volumes: pgdata
    healthcheck: pg_isready
    restart: unless-stopped
  
  app:
    build: .
    ports: 8000:8000
    environment:
      DATABASE_URL: postgresql+asyncpg://...@db:5432/shoptracker
      ENV: prod
    depends_on:
      db: condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## 6.3 환경별 설정 분리

```
.env.dev:
  DATABASE_URL=postgresql+asyncpg://shoptracker:shoptracker@localhost:5432/shoptracker
  ENV=dev
  DEBUG=true

.env.prod:
  DATABASE_URL=postgresql+asyncpg://shoptracker:${DB_PASSWORD}@db:5432/shoptracker
  ENV=prod
  DEBUG=false
```

### structlog 환경별 분기

```
if config.ENV == "prod":
    renderer = structlog.processors.JSONRenderer()
else:
    renderer = structlog.dev.ConsoleRenderer()
```

---

## 6.4 Gunicorn 설정

```
gunicorn.conf.py:
  bind = "0.0.0.0:8000"
  workers = 4
  worker_class = "uvicorn.workers.UvicornWorker"
  accesslog = "-"
  errorlog = "-"
  loglevel = "info"
  keepalive = 5
  graceful_timeout = 30
  timeout = 60
```

---

## 6.5 Health Check

```
GET /health → 200 {"status": "ok"}
GET /health/db → DB 연결 확인 (SELECT 1)

docker-compose healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

---

## 6.6 Alembic 마이그레이션 실행

```bash
# 마이그레이션 생성
docker compose exec app alembic revision --autogenerate -m "initial"

# 마이그레이션 적용
docker compose exec app alembic upgrade head

# 롤백
docker compose exec app alembic downgrade -1
```

---

## 6.7 실행 순서

```bash
# 1. 빌드
docker compose build

# 2. 실행
docker compose up -d

# 3. 마이그레이션
docker compose exec app alembic upgrade head

# 4. 확인
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI

# 5. 로그 확인
docker compose logs -f app
```

---

## 6.8 E2E 테스트 (Docker 환경 대상)

### tests/e2e/test_api.py

```
핵심:
  - 실제 PostgreSQL 대상 (docker compose 환경)
  - 전체 시나리오:
    1. 구독 생성 (Premium)
    2. 주문 생성
    3. 자동 결제 확인 (10% 할인)
    4. 자동 배송 생성 확인 (무료)
    5. 배송 상태 변경 시뮬레이션
    6. Tracking 타임라인 확인
  - httpx.AsyncClient(base_url="http://localhost:8000")
```

---

## 6.9 Phase 6 완료 기준

- [ ] Dockerfile (multi-stage build)
- [ ] docker-compose.yml (PostgreSQL + App)
- [ ] Gunicorn + Uvicorn workers 설정
- [ ] 환경별 설정 (.env.dev, .env.prod)
- [ ] Health check 엔드포인트 (/health, /health/db)
- [ ] Alembic 마이그레이션 실행 확인
- [ ] E2E 테스트 (Docker 환경)
- [ ] Swagger UI 접근 확인