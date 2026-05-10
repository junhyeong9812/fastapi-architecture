from decimal import Decimal
from uuid import uuid4
import pytest
from app.shared.value_objects import Money
from app.shipping.domain.entities import Shipment, ShipmentStatus, Address


class TestShipmentCreation:
    def test_create(self):
        """배송 생성 → PREPARING 상태."""
        shipment = Shipment.create(
            order_id=uuid4(),
            address=Address(street="서울 강남구", city="서울", zip_code="06000"),
            shipping_fee=Money(Decimal("3000")),
            original_fee=Money(Decimal("3000")),
            fee_discount_type="none",
        )
        assert shipment.status == ShipmentStatus.PREPARING


class TestShipmentStatusTransition:
    """PREPARING → IN_TRANSIT → DELIVERED."""

    def _make_shipment(self) -> Shipment:
        return Shipment.create(
            order_id=uuid4(),
            address=Address(street="서울 강남구", city="서울", zip_code="06000"),
            shipping_fee=Money(Decimal("0")),
            original_fee=Money(Decimal("3000")),
            fee_discount_type="premium_free",
        )

    def test_preparing_to_in_transit(self):
        s = self._make_shipment()
        s.mark_in_transit("TRACK123")
        assert s.status == ShipmentStatus.IN_TRANSIT
        assert s.tracking_number == "TRACK123"

    def test_in_transit_to_delivered(self):
        s = self._make_shipment()
        s.mark_in_transit("TRACK123")
        s.mark_delivered()
        assert s.status == ShipmentStatus.DELIVERED

    def test_skip_raises(self):
        """PREPARING에서 바로 DELIVERED 불가."""
        s = self._make_shipment()
        with pytest.raises(Exception):
            s.mark_delivered()