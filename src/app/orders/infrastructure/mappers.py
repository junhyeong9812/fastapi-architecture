"""Entity ↔ ORM Model 변환.

★ 학습 포인트:
도메인 엔티티(Order)와 ORM 모델(OrderModel)은 별개 세계.
이 mapper가 두 세계를 변환한다.

order_to_model: Order → OrderModel (저장할 때)
model_to_order: OrderModel → Order (조회할 때)

Money(Decimal) ↔ float 변환도 여기서 처리한다.
Decimal은 정밀하고, float는 DB에 저장하기 쉽다.
"""

from decimal import Decimal
from uuid import UUID
from app.orders.domain.entities import Order, OrderItem
from app.shared.value_objects import Money
from app.orders.domain.value_objects import  OrderStatus
from app.orders.infrastructure.models import OrderModel, OrderItemModel


def order_to_model(order: Order) -> OrderModel:
    """도메인 엔티티 → ORM 모델. DB 저장용."""
    return OrderModel(
        id=str(order.id),                               # UUID → str
        customer_name=order.customer_name,
        status=order.status.value,                       # Enum → str
        total_amount=float(order.total_amount.amount),   # Decimal → float
        currency=order.total_amount.currency,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemModel(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price.amount),
                currency=item.unit_price.currency,
            )
            for item in order.items
        ],
    )


def model_to_order(model: OrderModel) -> Order:
    """ORM 모델 → 도메인 엔티티. DB 조회 후 복원용."""
    items = [
        OrderItem(
            product_name=item.product_name,
            quantity=item.quantity,
            # str(float) → Decimal: 부동소수점 오차 방지
            unit_price=Money(Decimal(str(item.unit_price)), item.currency),
        )
        for item in model.items
    ]
    return Order(
        id=UUID(model.id),                              # str → UUID
        customer_name=model.customer_name,
        items=items,
        status=OrderStatus(model.status),                # str → Enum
        total_amount=Money(Decimal(str(model.total_amount)), model.currency),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )