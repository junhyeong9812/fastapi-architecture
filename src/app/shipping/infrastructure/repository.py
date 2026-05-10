from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.shipping.domain.entities import Shipment
from app.shipping.infrastructure.models import ShipmentModel
from app.shipping.infrastructure.mappers import shipment_to_model, model_to_shipment


class SQLAlchemyShipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, shipment: Shipment) -> None:
        self._session.add(shipment_to_model(shipment))
        await self._session.flush()

    async def find_by_id(self, shipment_id: UUID) -> Shipment | None:
        model = await self._session.get(ShipmentModel, str(shipment_id))
        return model_to_shipment(model) if model else None

    async def find_by_order_id(self, order_id: UUID) -> Shipment | None:
        stmt = select(ShipmentModel).where(ShipmentModel.order_id == str(order_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model_to_shipment(model) if model else None

    async def update(self, shipment: Shipment) -> None:
        model = await self._session.get(ShipmentModel, str(shipment.id))
        if model is None:
            return
        model.status = shipment.status.value
        model.tracking_number = shipment.tracking_number
        await self._session.flush()