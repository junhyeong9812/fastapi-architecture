"""structlog 기반 요청/응답 로깅 미들웨어.

★ 학습 포인트:
모든 HTTP 요청이 이 미들웨어를 통과한다.
요청 시작 시각과 완료 시각을 기록하여 응답 시간을 측정한다.
Spring의 HandlerInterceptor 또는 Servlet Filter와 같은 역할.

structlog는 일반 print/logging 대신 구조화된 로그를 출력한다.
JSON 형태로 출력할 수 있어서 로그 분석 도구(ELK 등)와 궁합이 좋다.
"""

import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 요청마다 고유 ID 생성 (로그 추적용)
        request_id = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 요청 시작 시각 기록
        start = time.perf_counter()

        # 요청 시작 로그
        logger.info(
            "request_started",              # 이벤트 이름 (로그 검색 키)
            method=request.method,          # GET, POST 등
            path=request.url.path,          # /api/v1/orders/ 등
        )

        # 다음 미들웨어 또는 실제 라우터 핸들러 실행
        response: Response = await call_next(request)

        # 소요 시간 계산 (밀리초)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # 요청 완료 로그
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,    # 200, 404 등
            elapsed_ms=elapsed_ms,          # 응답 시간
        )
        return response