from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka

from app.shared.di_container import create_container
from app.shared.middleware import LoggingMiddleware
from app.orders.presentation.router import router as orders_router
from app.subscriptions.presentation.router import router as subscriptions_router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(0,)
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()

# FastAPI 앱 생성
app = FastAPI(
    title="ShopTracker",
    version="0.1.0",
    lifespan=lifespan,
)

# 미들웨어 등록 — 모든 요청에 로깅 적용
app.add_middleware(LoggingMiddleware)

# DI 컨테이너 생성 + FastAPI에 연결
container = create_container()
setup_dishka(container, app)

# 라우터 등록 — 각 모듈의 API 엔드포인트
app.include_router(orders_router)
app.include_router(subscriptions_router)


@app.get("/health")
async def health():
    """헬스 체크. 서버가 살아있는지 확인용."""
    return {"status": "ok"}