"""OrderTracking 엔티티 테스트."""

from uuid import uuid4
import pytest
from app.tracking.domain.entities import (
    OrderTracking, TrackingPhase, TrackingEvent,
)


class TestTrackingCreation:
    def test_create(self):
        """추적 생성 → ORDER_PLACED 상태."""
        tracking = OrderTracking.create(
            order_id=uuid4(),
            customer_name="홍길동",
            subscription_tier="premium",
        )
        assert tracking.current_phase == TrackingPhase.ORDER_PLACED
        assert len(tracking.events) == 0   # 생성 시 이벤트 없음


class TestTrackingEvents:
    def _make_tracking(self) -> OrderTracking:
        return OrderTracking.create(
            order_id=uuid4(),
            customer_name="홍길동",
            subscription_tier="none",
        )

    def test_add_event(self):
        """이벤트 추가."""
        t = self._make_tracking()
        t.add_event("order.created", "orders", {"amount": 100000})
        assert len(t.events) == 1
        assert t.events[0].event_type == "order.created"
        assert t.events[0].module == "orders"

    def test_mark_failed(self):
        """실패 처리 → FAILED 상태."""
        t = self._make_tracking()
        t.mark_failed("결제 거절")
        assert t.current_phase == TrackingPhase.FAILED

    def test_mark_completed(self):
        """완료 처리 → DELIVERED + completed_at 설정."""
        t = self._make_tracking()
        t.current_phase = TrackingPhase.SHIPPING
        t.mark_completed()
        assert t.current_phase == TrackingPhase.DELIVERED
        assert t.completed_at is not None

    def test_events_ordered(self):
        """이벤트가 추가 순서대로 기록된다."""
        t = self._make_tracking()
        t.add_event("order.created", "orders", {})
        t.add_event("payment.approved", "payments", {})
        t.add_event("shipment.created", "shipping", {})
        assert len(t.events) == 3
        assert t.events[0].event_type == "order.created"
        assert t.events[2].event_type == "shipment.created"