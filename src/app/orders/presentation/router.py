"""FastAPI Router.

★ 핵심 학습 포인트:
라우터는 얇다(Thin Controller). 비즈니스 로직이 없다.
1. HTTP 요청을 받아서
2. Command/Query로 변환하고
3. Handler에 위임한 뒤
4. 결과를 Response로 변환하여 반환

DishkaRoute: Dishka DI가 핸들러를 자동 주입하기 위한 Route 클래스.
FromDishka[T]: "T 타입의 인스턴스를 DI 컨테이너에서 가져와줘"라는 의미.
"""

from decimal import Decimal
from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from app.orders.domain.entities import Order
from app.orders.domain.exceptions import (
    OrderNotFoundError, InvalidOrderError, InvalidStatusTransition,
)
from app.orders.application.commands import (
    CreateOrderCommand, CancelOrderCommand, OrderItemDTO,
)
from app.orders.application.queries import GetOrderQuery, ListOrdersQuery
from app.orders.application.command_handlers import (
    CreateOrderHandler, CancelOrderHandler,
)
from app.orders.application.query_handlers import (
    GetOrderHandler, ListOrdersHandler,
)
from app.orders.presentation.schemas import (
    CreateOrderRequest, OrderResponse, OrderItemResponse, OrderListResponse,
)

# prefix: 이 라우터의 모든 엔드포인트 앞에 붙는 경로
# tags: Swagger UI에서 그룹핑 이름
# route_class=DishkaRoute: Dishka DI가 동작하기 위한 설정
router = APIRouter(prefix="/api/v1/orders", tags=["Orders"],
                   route_class=DishkaRoute)


def _order_to_response(order: Order) -> OrderResponse:
    """도메인 엔티티 → HTTP 응답 DTO 변환 헬퍼."""
    return OrderResponse(
        id=str(order.id),
        customer_name=order.customer_name,
        status=order.status.value,
        total_amount=float(order.total_amount.amount),
        currency=order.total_amount.currency,
        items=[
            OrderItemResponse(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price.amount),
                subtotal=float(item.subtotal.amount),
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/", status_code=201)
async def create_order(
    body: CreateOrderRequest,                       # FastAPI가 JSON → Pydantic 변환
    handler: FromDishka[CreateOrderHandler],         # DI가 핸들러 주입
) -> OrderResponse:
    """주문 생성 API. POST /api/v1/orders/"""
    try:
        # Pydantic DTO → Application Command로 변환
        command = CreateOrderCommand(
            customer_name=body.customer_name,
            items=[
                OrderItemDTO(
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=Decimal(str(item.unit_price)),
                )
                for item in body.items
            ],
        )
        order_id = await handler.handle(command)

        # 생성된 주문을 조회하여 응답
        order = await handler._repo.find_by_id(order_id)
        return _order_to_response(order)
    except InvalidOrderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_orders(
    handler: FromDishka[ListOrdersHandler],
    customer_name: str | None = None,       # 쿼리 파라미터 (선택)
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> OrderListResponse:
    """주문 목록 조회. GET /api/v1/orders/?customer_name=홍길동&page=1"""
    query = ListOrdersQuery(
        customer_name=customer_name, status=status, page=page, size=size
    )
    result = await handler.handle(query)
    return OrderListResponse(
        items=[_order_to_response(o) for o in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.get("/{order_id}")
async def get_order(
    order_id: str,                                  # URL 경로 파라미터
    handler: FromDishka[GetOrderHandler],
) -> OrderResponse:
    """주문 상세 조회. GET /api/v1/orders/{order_id}"""
    try:
        order = await handler.handle(GetOrderQuery(order_id=order_id))
        return _order_to_response(order)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    handler: FromDishka[CancelOrderHandler],
) -> OrderResponse:
    """주문 취소. POST /api/v1/orders/{order_id}/cancel"""
    try:
        await handler.handle(CancelOrderCommand(order_id=order_id))
        # 취소 후 상태를 다시 조회하여 반환
        order = await handler._repo.find_by_id(
            __import__("uuid").UUID(order_id)
        )
        return _order_to_response(order)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))