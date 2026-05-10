"""추적 엔티티.

OrderTracking은 주문의 전체 여정을 기록한다.
events 리스트에 발생한 모든 이벤트가 시간순으로 쌓인다.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4


class TrackingPhase(str, Enum):
    """추적 상태. 주문의 현재 단계."""
    ORDER_PLACED = "order_placed"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_COMPLETED = "payment_completed"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class TrackingEvent:
    """타임라인의 개별 이벤트."""
    event_type: str         # "order.created", "payment.approved" 등
    timestamp: datetime
    module: str             # "orders", "payments", "shipping"
    detail: dict            # 이벤트별 상세 데이터


@dataclass
class OrderTracking:
    """주문 추적 Aggregate."""
    id: UUID
    order_id: UUID
    customer_name: str
    subscription_tier: str
    events: list[TrackingEvent]
    current_phase: TrackingPhase
    started_at: datetime
    completed_at: datetime | None

    @classmethod
    def create(
        cls, order_id: UUID, customer_name: str, subscription_tier: str,
    ) -> "OrderTracking":
        return cls(
            id=uuid4(), order_id=order_id,
            customer_name=customer_name,
            subscription_tier=subscription_tier,
            events=[],
            current_phase=TrackingPhase.ORDER_PLACED,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

    def add_event(self, event_type: str, module: str, detail: dict) -> None:
        """타임라인에 이벤트 추가."""
        self.events.append(
            TrackingEvent(
                event_type=event_type,
                timestamp=datetime.now(UTC),
                module=module,
                detail=detail,
            )
        )

    def mark_failed(self, reason: str) -> None:
        """실패 처리. 결제 거절 등."""
        self.current_phase = TrackingPhase.FAILED
        self.add_event("tracking.failed", "tracking", {"reason": reason})

    def mark_completed(self) -> None:
        """완료 처리. 배송 완료."""
        self.current_phase = TrackingPhase.DELIVERED
        self.completed_at = datetime.now(UTC)