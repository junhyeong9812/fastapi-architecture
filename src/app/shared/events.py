"""도메인 이벤트 정의.

★ 학습 포인트:
이벤트는 "이런 일이 일어났다"는 과거형 사실(fact)이다.
- OrderCreatedEvent: "주문이 생성되었다"
- PaymentApprovedEvent: "결제가 승인되었다"

발행자(publisher)와 수신자(subscriber)가 서로를 모른 채,
이 이벤트 구조만 합의하면 통신할 수 있다.
shared에 정의하는 이유: 모든 모듈이 이 계약을 참조하기 위해.

모든 이벤트는 frozen=True (불변) dataclass.
이벤트는 한번 생성되면 수정되지 않아야 한다.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# ============================================================
# Phase 1: Orders + Subscriptions 이벤트
# ============================================================

@dataclass(frozen=True)
class OrderCreatedEvent:
    """주문 생성 시 발행. Payments가 구독하여 자동 결제 시작."""
    order_id: UUID
    customer_name: str
    total_amount: Decimal       # 주문 총액
    items_count: int            # 주문 항목 수
    timestamp: datetime


@dataclass(frozen=True)
class OrderCancelledEvent:
    """주문 취소 시 발행."""
    order_id: UUID
    reason: str
    timestamp: datetime


@dataclass(frozen=True)
class SubscriptionActivatedEvent:
    """구독 활성화 시 발행."""
    subscription_id: UUID
    customer_name: str
    tier: str                   # "basic" / "premium"
    expires_at: datetime
    timestamp: datetime


@dataclass(frozen=True)
class SubscriptionExpiredEvent:
    """구독 만료 시 발행 (업그레이드할 때 기존 구독이 만료됨)."""
    subscription_id: UUID
    customer_name: str
    previous_tier: str
    timestamp: datetime


# ============================================================
# Phase 2: Payments 이벤트
# ============================================================

@dataclass(frozen=True)
class PaymentApprovedEvent:
    """결제 승인 시 발행. Shipping이 구독하여 배송 자동 생성."""
    payment_id: UUID
    order_id: UUID
    original_amount: Decimal    # 할인 전 금액
    discount_amount: Decimal    # 할인 금액
    final_amount: Decimal       # 실제 결제 금액
    applied_discount_type: str  # "none", "basic_subscription", "premium_subscription"
    method: str                 # "credit_card", "bank_transfer"
    timestamp: datetime


@dataclass(frozen=True)
class PaymentRejectedEvent:
    """결제 거절 시 발행. Orders가 구독하여 주문을 자동 취소."""
    payment_id: UUID
    order_id: UUID
    reason: str                 # "잔액 부족" 등
    timestamp: datetime


# ============================================================
# Phase 3: Shipping 이벤트
# ============================================================

@dataclass(frozen=True)
class ShipmentCreatedEvent:
    """배송 생성 시 발행."""
    shipment_id: UUID
    order_id: UUID
    shipping_fee: Decimal       # 실제 배송비
    fee_discount_type: str      # "none", "basic_half", "premium_free"
    tracking_number: str | None
    timestamp: datetime


@dataclass(frozen=True)
class ShipmentStatusChangedEvent:
    """배송 상태 변경 시 발행."""
    shipment_id: UUID
    order_id: UUID
    new_status: str             # "in_transit", "delivered"
    timestamp: datetime