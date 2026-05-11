"""글로벌 예외 핸들러.

각 router의 try-except를 제거하고 여기서 일괄 처리.
모든 도메인 예외 → 표준 에러 응답 형식으로 변환.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.orders.domain.exceptions import (
    OrderNotFoundError, InvalidOrderError, InvalidStatusTransition,
)
from app.subscriptions.domain.entities import (
    SubscriptionNotFoundError, InvalidSubscriptionError,
)
from app.payments.domain.exceptions import PaymentNotFoundError
from app.shipping.domain.exceptions import ShipmentNotFoundError
from app.tracking.domain.exceptions import TrackingNotFoundError


def error_response(code: str, message: str, detail: dict | None = None) -> dict:
    """표준 에러 응답 형식."""
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    """앱에 글로벌 예외 핸들러 등록. main.py에서 호출."""

    @app.exception_handler(OrderNotFoundError)
    async def _(req: Request, exc: OrderNotFoundError):
        return JSONResponse(404, error_response("ORDER_NOT_FOUND", str(exc)))

    @app.exception_handler(InvalidOrderError)
    async def _(req: Request, exc: InvalidOrderError):
        return JSONResponse(400, error_response("INVALID_ORDER", str(exc)))

    @app.exception_handler(InvalidStatusTransition)
    async def _(req: Request, exc: InvalidStatusTransition):
        return JSONResponse(400, error_response("INVALID_TRANSITION", str(exc)))

    @app.exception_handler(SubscriptionNotFoundError)
    async def _(req: Request, exc: SubscriptionNotFoundError):
        return JSONResponse(404, error_response("SUBSCRIPTION_NOT_FOUND", str(exc)))

    @app.exception_handler(InvalidSubscriptionError)
    async def _(req: Request, exc: InvalidSubscriptionError):
        return JSONResponse(400, error_response("INVALID_SUBSCRIPTION", str(exc)))

    @app.exception_handler(PaymentNotFoundError)
    async def _(req: Request, exc: PaymentNotFoundError):
        return JSONResponse(404, error_response("PAYMENT_NOT_FOUND", str(exc)))

    @app.exception_handler(ShipmentNotFoundError)
    async def _(req: Request, exc: ShipmentNotFoundError):
        return JSONResponse(404, error_response("SHIPMENT_NOT_FOUND", str(exc)))

    @app.exception_handler(TrackingNotFoundError)
    async def _(req: Request, exc: TrackingNotFoundError):
        return JSONResponse(404, error_response("TRACKING_NOT_FOUND", str(exc)))

    @app.exception_handler(Exception)
    async def _(req: Request, exc: Exception):
        import structlog
        structlog.get_logger().error("unhandled_exception", error=str(exc))
        return JSONResponse(500, error_response("INTERNAL_ERROR", "서버 오류"))