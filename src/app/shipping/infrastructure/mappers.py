from decimal import Decimal
from uuid import UUID
from app.shared.value_objects import Money
from app.shipping.domain.entities import Shipment, ShipmentStatus, Address
from app.shipping.infrastructure.models import ShipmentModel


def shipment_to_model(s: Shipment) -> ShipmentModel:
    return ShipmentModel(
        id=str(s.id), order_id=str(s.order_id), status=s.status.value,
        street=s.address.street, city=s.address.city, zip_code=s.address.zip_code,
        shipping_fee=float(s.shipping_fee.amount),
        original_fee=float(s.original_fee.amount),
        fee_discount_type=s.fee_discount_type, currency=s.shipping_fee.currency,
        tracking_number=s.tracking_number, estimated_delivery=s.estimated_delivery)


def model_to_shipment(m: ShipmentModel) -> Shipment:
    return Shipment(
        id=UUID(m.id), order_id=UUID(m.order_id), status=ShipmentStatus(m.status),
        address=Address(street=m.street, city=m.city, zip_code=m.zip_code),
        shipping_fee=Money(Decimal(str(m.shipping_fee)), m.currency),
        original_fee=Money(Decimal(str(m.original_fee)), m.currency),
        fee_discount_type=m.fee_discount_type,
        tracking_number=m.tracking_number, estimated_delivery=m.estimated_delivery)