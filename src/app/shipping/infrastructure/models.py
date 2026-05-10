import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import Base


class ShipmentModel(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="preparing")
    street: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(50))
    zip_code: Mapped[str] = mapped_column(String(10))
    shipping_fee: Mapped[float] = mapped_column(Numeric(12, 2))
    original_fee: Mapped[float] = mapped_column(Numeric(12, 2))
    fee_discount_type: Mapped[str] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)