from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from enum import Enum
from uuid import UUID, uuid4

class SubscriptionTier(str, Enum):
    """구독 등급. str 상속으로 JSON/DB 직렬화 용이."""
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"

class SubscriptionStatus(str, Enum):
    """구독 상태."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SubscriptionError(Exception):
    """구독 도메인 기본 예외."""
    pass

class InvalidSubscriptionError(SubscriptionError):
    """생성/변경 규칙 위반."""
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)

class SubscriptionNotFoundError(SubscriptionError):
    """조회 실패."""
    def __init__(self, subscription_id: str) -> None:
        self.subscription_id = subscription_id
        super().__init__(f"구독을 찾을 수 없습니다: {subscription_id}")

@dataclass
class Subscription:
    """구독 엔티티."""
    id: UUID
    customer_name: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    started_at: datetime
    expires_at: datetime

    @classmethod
    def create(
        cls,
        customer_name: str,
        tier: SubscriptionTier,
        duration_days: int = 30,
    ) -> "Subscription":
        """팩토리 메서드. 생성 규칙을 강제한다."""
        if not customer_name or not customer_name.strip():
            raise InvalidSubscriptionError("고객 이름이 비어있습니다.")
        if tier == SubscriptionTier.NONE:
            raise InvalidSubscriptionError("NONE 등급으로 구독을 생성할 수 없습니다.")

        now = datetime.now(UTC)
        return cls(
            id = uuid4(),
            customer_name = customer_name.strip(),
            tier = tier,
            status= SubscriptionStatus.ACTIVE,
            started_at = now,
            expires_at = now + timedelta(days=duration_days),
        )

    def is_active(self) -> bool:
        now = datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.status == SubscriptionStatus.ACTIVE and expires > now

    def cancel(self) -> None:
        """구독 취소. 활성 상태에서만 가능."""
        if self.status != SubscriptionStatus.ACTIVE:
            raise InvalidSubscriptionError("활성 상태가 아닌 구독은 취소할 수 없습니다")
        self.status = SubscriptionStatus.CANCELLED

    def expire(self) -> None:
        """구독 만료 처리.
        업그레이드(Basic→Premium) 시 기존 구독을 만료시킬 때 사용.
        """
        self.status = SubscriptionStatus.EXPIRED