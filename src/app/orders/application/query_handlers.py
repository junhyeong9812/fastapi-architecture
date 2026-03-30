"""Query 처리 (읽기 전용).

★ CQRS 포인트:
Query 핸들러는 EventBus가 없다!
Command 핸들러: repo + event_bus
Query 핸들러: repo만
읽기는 부수효과 없이 데이터만 반환한다.
"""

from dataclasses import dataclass
from uuid import UUID

from app.orders.domain.entities import Order
from app.orders.domain.exceptions import OrderNotFoundError
from app.orders.domain.interfaces import OrderReadRepositoryProtocol
from app.orders.application.queries import GetOrderQuery, ListOrdersQuery


@dataclass
class PaginatedOrders:
    """페이지네이션된 주문 목록 결과."""
    items: list[Order]
    total: int
    page: int
    size: int


class GetOrderHandler:
    """단건 주문 조회."""
    def __init__(self, repo: OrderReadRepositoryProtocol) -> None:
        self._repo = repo       # ★ EventBus 없음!

    async def handle(self, query: GetOrderQuery) -> Order:
        order = await self._repo.find_by_id(UUID(query.order_id))
        if order is None:
            raise OrderNotFoundError(query.order_id)
        return order


class ListOrdersHandler:
    """주문 목록 조회 (페이지네이션)."""
    def __init__(self, repo: OrderReadRepositoryProtocol) -> None:
        self._repo = repo       # ★ EventBus 없음!

    async def handle(self, query: ListOrdersQuery) -> PaginatedOrders:
        items = await self._repo.list_orders(
            customer_name=query.customer_name,
            status=query.status,
            page=query.page,
            size=query.size,
        )
        total = await self._repo.count_orders(
            customer_name=query.customer_name,
            status=query.status,
        )
        return PaginatedOrders(
            items=items, total=total, page=query.page, size=query.size
        )