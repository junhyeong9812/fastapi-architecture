"""SQLAlchemy Repository 구현체 (Driven Adapter).

★ 학습 포인트 (Hexagonal Architecture):
이것은 "어댑터(Adapter)"이다.
domain/interfaces.py에 정의된 "포트(Port)"의 실제 구현.
SQLAlchemy를 사용하여 DB에 접근한다.

도메인 코드(entities, handlers)는 이 구현체를 직접 참조하지 않는다.
DI 컨테이너가 "이 Port에는 이 Adapter를 연결해"라고 설정한다.
"""

from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.orders.domain.entities import Order
from app.orders.infrastructure.models import OrderModel
from app.orders.infrastructure.mappers import order_to_model, model_to_order


class SQLAlchemyOrderRepository:
    """OrderRepositoryProtocol + OrderReadRepositoryProtocol을 동시에 충족.

    Phase 1에서는 하나의 구현체가 읽기/쓰기 모두 처리.
    나중에 CQRS를 더 발전시키면 읽기 전용 Repository를 분리할 수 있다.
    """

    def __init__(self, session: AsyncSession) -> None:
        # DI가 요청마다 새 session을 주입한다
        self._session = session

    async def save(self, order: Order) -> None:
        """도메인 엔티티를 DB에 저장."""
        model = order_to_model(order)   # Entity → ORM Model
        self._session.add(model)        # 세션에 추가
        await self._session.flush()     # DB에 즉시 반영 (commit은 DI가 관리)

    async def find_by_id(self, order_id: UUID) -> Order | None:
        """PK로 주문 조회."""
        model = await self._session.get(OrderModel, str(order_id))
        if model is None:
            return None
        return model_to_order(model)    # ORM Model → Entity

    async def update(self, order: Order) -> None:
        """기존 주문 업데이트. 상태 변경 등."""
        model = await self._session.get(OrderModel, str(order.id))
        if model is None:
            return
        model.status = order.status.value
        model.total_amount = float(order.total_amount.amount)
        model.updated_at = order.updated_at
        await self._session.flush()

    async def list_orders(
        self,
        customer_name: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[Order]:
        """주문 목록 조회 (필터 + 페이지네이션)."""
        stmt = select(OrderModel)
        if customer_name:
            stmt = stmt.where(OrderModel.customer_name == customer_name)
        if status:
            stmt = stmt.where(OrderModel.status == status)
        stmt = stmt.order_by(OrderModel.created_at.desc())  # 최신순
        stmt = stmt.offset((page - 1) * size).limit(size)   # 페이지네이션
        result = await self._session.execute(stmt)
        return [model_to_order(m) for m in result.scalars().all()]

    async def count_orders(
        self,
        customer_name: str | None = None,
        status: str | None = None,
    ) -> int:
        """조건에 맞는 주문 수 (페이지네이션의 total에 사용)."""
        stmt = select(func.count()).select_from(OrderModel)
        if customer_name:
            stmt = stmt.where(OrderModel.customer_name == customer_name)
        if status:
            stmt = stmt.where(OrderModel.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()