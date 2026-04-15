from uuid import UUID
from app.subscriptions.domain.entities import (
    Subscription, SubscriptionTier, SubscriptionStatus,
)
from app.subscriptions.infrastructure.models import SubscriptionModel

def subscription_to_model(sub: Subscription) -> SubscriptionModel:
    """도메인 엔티티 -> ORM 모델."""
    return SubscriptionModel(
        id = str(sub.id),
        customer_name=sub.customer_name,
        tier=sub.tier.value,
        status=sub.status.value,
        started_at=sub.started_at,
        expires_at=sub.expires_at,
    )

def model_to_subscription(model: SubscriptionModel) -> Subscription:
    """ORM 모델 -> 도메인 엔티티."""
    return Subscription(
        id=UUID(model.id),
        customer_name=model.customer_name,
        tier=SubscriptionTier(model.tier),
        status=SubscriptionStatus(model.status),
        started_at=model.started_at,
        expires_at=model.expires_at,
    )