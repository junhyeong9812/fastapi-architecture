from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.subscriptions.domain.entities import Subscription
from app.subscriptions.infrastructure.models import SubscriptionModel
from app.subscriptions.infrastructure.mappers import (
    subscription_to_model, model_to_subscription,
)

class SQLAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, subscription: Subscription) -> None:
        model = subscription_to_model(subscription)
        self._session.add(model)
        await self._session.flush()

    async def find_by_id(self, subscription_id:UUID) -> Subscription | None:
        model = await self._session.get(SubscriptionModel, str(subscription_id))
        if model is None:
            return None
        return model_to_subscription(model)

    async def find_active_by_customer(self, customer_name: str) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.customer_name == customer_name)
            .where(SubscriptionModel.status == "active")
            .order_by(SubscriptionModel.started_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_subscription(model)

    async def update(self, subscription: Subscription) -> None:
        model = await self._session.get(SubscriptionModel, str(subscription.id))
        if model is None:
            return
        model.tier = subscription.tier.value
        model.status = subscription.status.value
        model.expires_at = subscription.expires_at
        await self._session.flush()