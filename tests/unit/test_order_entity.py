"""Order 엔티티 테스트.

★ 학습 포인트:
이 테스트는 DB 없이 순수 Python만으로 실행된다.
import fastapi, import sqlalchemy가 없다.
도메인 로직이 프레임워크에 의존하지 않는다는 증거이다.
"""

from decimal import Decimal
import pytest
from app.orders.domain.entities import Order, OrderItem
from app.shared.value_objects import Money
from app.orders.domain.value_objects import OrderStatus
from app.orders.domain.exceptions import (
    InvalidOrderError,
    InvalidStatusTransition,
)


class TestOrderCreation:
    """주문 생성 규칙 테스트."""

    def test_create_order_success(self):
        """정상 주문 생성. 상태는 CREATED, 총액 자동 계산."""
        items = [
            OrderItem(
                product_name="키보드",
                quantity=1,
                unit_price=Money(Decimal("150000")),
            ),
        ]
        order = Order.create(customer_name="홍길동", items=items)

        assert order.customer_name == "홍길동"
        assert order.status == OrderStatus.CREATED
        assert order.total_amount == Money(Decimal("150000"))
        assert len(order.items) == 1
        assert order.id is not None  # UUID가 자동 생성됨

    def test_create_order_multiple_items(self):
        """복수 항목 주문. 총액 = 각 항목의 (단가 × 수량) 합계."""
        items = [
            OrderItem(
                product_name="키보드",
                quantity=2,
                unit_price=Money(Decimal("150000")),
            ),
            OrderItem(
                product_name="마우스",
                quantity=1,
                unit_price=Money(Decimal("50000")),
            ),
        ]
        order = Order.create(customer_name="홍길동", items=items)
        # 150000×2 + 50000×1 = 350000
        assert order.total_amount == Money(Decimal("350000"))

    def test_create_order_empty_name_raises(self):
        """고객 이름이 비어있으면 생성 불가."""
        items = [
            OrderItem(
                product_name="키보드",
                quantity=1,
                unit_price=Money(Decimal("150000")),
            ),
        ]
        with pytest.raises(InvalidOrderError, match="이름"):
            Order.create(customer_name="", items=items)

    def test_create_order_no_items_raises(self):
        """항목이 0개이면 생성 불가."""
        with pytest.raises(InvalidOrderError, match="항목"):
            Order.create(customer_name="홍길동", items=[])

    def test_create_order_zero_quantity_raises(self):
        """수량이 0이면 생성 불가."""
        items = [
            OrderItem(
                product_name="키보드",
                quantity=0,
                unit_price=Money(Decimal("150000")),
            ),
        ]
        with pytest.raises(InvalidOrderError, match="수량"):
            Order.create(customer_name="홍길동", items=items)


class TestOrderStatusTransition:
    """주문 상태 전이 테스트.

    ★ 상태 머신 규칙:
    CREATED → PAYMENT_PENDING → PAID → SHIPPING → DELIVERED
    CREATED / PAYMENT_PENDING → CANCELLED (PAID 이후 취소 불가)
    DELIVERED, CANCELLED → 종료 상태 (더 이상 전이 불가)
    """

    def _make_order(self) -> Order:
        """테스트용 주문 생성 헬퍼."""
        items = [
            OrderItem(
                product_name="키보드",
                quantity=1,
                unit_price=Money(Decimal("150000")),
            ),
        ]
        return Order.create(customer_name="홍길동", items=items)

    def test_created_to_payment_pending(self):
        """CREATED → PAYMENT_PENDING: 결제 대기 상태로 전환."""
        order = self._make_order()
        order.mark_payment_pending()
        assert order.status == OrderStatus.PAYMENT_PENDING

    def test_payment_pending_to_paid(self):
        """PAYMENT_PENDING → PAID: 결제 완료."""
        order = self._make_order()
        order.mark_payment_pending()
        order.mark_paid()
        assert order.status == OrderStatus.PAID

    def test_paid_to_shipping(self):
        """PAID → SHIPPING: 배송 시작."""
        order = self._make_order()
        order.mark_payment_pending()
        order.mark_paid()
        order.mark_shipping()
        assert order.status == OrderStatus.SHIPPING

    def test_shipping_to_delivered(self):
        """SHIPPING → DELIVERED: 배송 완료."""
        order = self._make_order()
        order.mark_payment_pending()
        order.mark_paid()
        order.mark_shipping()
        order.mark_delivered()
        assert order.status == OrderStatus.DELIVERED

    def test_cancel_from_created(self):
        """CREATED에서 취소 가능."""
        order = self._make_order()
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_from_payment_pending(self):
        """PAYMENT_PENDING에서 취소 가능."""
        order = self._make_order()
        order.mark_payment_pending()
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_from_paid_raises(self):
        """★ PAID 이후에는 취소 불가! 이것이 비즈니스 규칙."""
        order = self._make_order()
        order.mark_payment_pending()
        order.mark_paid()
        with pytest.raises(InvalidStatusTransition):
            order.cancel()

    def test_skip_status_raises(self):
        """CREATED에서 바로 DELIVERED로 갈 수 없다. 순서를 지켜야 함."""
        order = self._make_order()
        with pytest.raises(InvalidStatusTransition):
            order.mark_delivered()

    def test_delivered_is_terminal(self):
        """DELIVERED는 종료 상태. 더 이상 전이 불가."""
        order = self._make_order()
        order.mark_payment_pending()
        order.mark_paid()
        order.mark_shipping()
        order.mark_delivered()
        with pytest.raises(InvalidStatusTransition):
            order.cancel()