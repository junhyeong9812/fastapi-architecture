from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID

from app.subscriptions.domain.entities import (
    Subscription, SubscriptionTier, SubscriptionNotFoundError,
)
from app.subscriptions.domain.interfaces import SubscriptionRepositoryProtocol
from app.shared.event_bus import EventBus
from app.shared.events import SubscriptionActivatedEvent, SubscriptionExpiredEvent

@dataclass(frozen=True)
class CreateSubscriptionCommand:
    """구독 생성 명렁."""
    customer_name: str
    tier: str

@dataclass(frozen=True)
class CancelSubscriptionCommand:
    """구독 취소 명령."""
    subscription_id: str

@dataclass(frozen=True)
class GetSubscriptionQuery:
    """단건 구독 조회."""
    subscription_id: str

@dataclass(frozen=True)
class GetActiveSubscriptionQuery:
    """고객의 활성 구독 조회."""
    customer_name: str

class CreateSubscriptionHandler:
    """구독 생성 유스케이스"""
    def __init__(self, repo: SubscriptionRepositoryProtocol,
                 event_bus: EventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def handle(self, command: CreateSubscriptionCommand) -> UUID:
        # 1. 기존 활성 구독이 있으면 만료 처리
        existing = await self._repo.find_active_by_customer(command.customer_name)
        if existing:
            existing.expired()
            await self._repo.update(existing)
            await self._event_bus.publish(
                SubscriptionExpiredEvent(
                    subscription_id=existing.id,
                    customer_name=existing.customer_name,
                    previous_tier=existing.tier.value,
                    timestamp=datetime.now(UTC),
                )
            )

        # 2. 새 구독 생성
        sub = Subscription.create(
            customer_name=command.customer_name,
            tier=SubscriptionTier(command.tier),
        )
        await self._repo.save(sub)

        # 3. 이벤트 발행
        await self._event_bus.publish(
            SubscriptionActivatedEvent(
                subscription_id=sub.id,
                customer_name=sub.customer_name,
                tier=sub.tier.value,
                expires_at=sub.expires_at,
                timestamp=datetime.now(UTC),
            )
        )
        return sub.id

class CancelSubscriptionHandler:
    """구독 취소 유스케이스"""
    def __init__(self, repo: SubscriptionRepositoryProtocol,
                 event_bus: EventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def handle(self, command: CancelSubscriptionCommand) -> None:
        sub = await self._repo.find_by_id(UUID(command.subscription_id))
        if sub is None:
            raise SubscriptionNotFoundError(command.subscription_id)
        sub.cancel()
        await self._repo.update(sub)

class GetSubscriptionHandler:
    """단건 구독 조회. EventBus 없음 (CQRS: 읽기는 부수효과 없음)"""
    def __init__(self, repo: SubscriptionRepositoryProtocol) -> None:
        self._repo = repo

    async def handle(self, query: GetSubscriptionQuery) -> Subscription:
        sub = await self._repo.find_by_id(UUID(query.subscription_id))
        if sub is None:
            raise SubscriptionNotFoundError(query.subscription_id)
        return sub

class GetActiveSubscriptionHandler:
    """고객의 현재 활성 구독 조회. 없으면 None 반환."""
    def __init__(self, repo: SubscriptionRepositoryProtocol) -> None:
        self._repo = repo

    async def handle(self, query: GetActiveSubscriptionQuery) -> Subscription | None:
        return await self._repo.find_active_by_customer(query.customer_name)