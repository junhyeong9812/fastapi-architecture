from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.payments.domain.entities import Payment
from app.payments.infrastructure.models import PaymentModel
from app.payments.infrastructure.mappers import payment_to_model, model_to_payment


class SQLAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, payment: Payment) -> None:
        self._session.add(payment_to_model(payment))
        await self._session.flush()

    async def find_by_id(self, payment_id: UUID) -> Payment | None:
        model = await self._session.get(PaymentModel, str(payment_id))
        return model_to_payment(model) if model else None

    async def find_by_order_id(self, order_id: UUID) -> Payment | None:
        stmt = select(PaymentModel).where(PaymentModel.order_id == str(order_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_payment(model) if model else None