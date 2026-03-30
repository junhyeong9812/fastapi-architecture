"""SQLAlchemy ORM 모델.

★ 핵심 학습 포인트:
도메인 엔티티(Order)와 ORM 모델(OrderModel)은 완전히 별개 클래스다.
- Order: 비즈니스 로직을 가진 순수 Python 클래스
- OrderModel: DB 테이블과 1:1 매핑되는 SQLAlchemy 클래스

이 둘을 분리하는 이유:
- Order는 SQLAlchemy를 모르고, OrderModel은 비즈니스 로직이 없다
- DB 스키마 변경이 도메인 로직에 영향을 주지 않는다
- 테스트에서 DB 없이 도메인 로직만 테스트할 수 있다

mapper.py가 이 두 세계를 변환(매핑)한다.
"""

import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Numeric, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.base_model import Base


class OrderModel(Base):
    """orders 테이블. 주문 정보."""
    __tablename__ = "orders"

    # String(36): UUID 문자열 길이. "550e8400-e29b-41d4-a716-446655440000"
    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    customer_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="created")
    # Numeric(12, 2): 최대 12자리, 소수점 2자리. 9,999,999,999.99까지
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC))

    # relationship: OrderModel과 OrderItemModel을 연결
    # cascade="all, delete-orphan": 주문 삭제 시 항목도 함께 삭제
    # lazy="selectin": 주문 조회 시 항목도 함께 로드 (N+1 문제 방지)
    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin")


class OrderItemModel(Base):
    """order_items 테이블. 주문 항목."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ForeignKey: orders 테이블의 id를 참조
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="KRW")

    # back_populates: OrderModel.items와 양방향 연결
    order: Mapped["OrderModel"] = relationship(back_populates="items")