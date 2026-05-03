import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import Base


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), index=True)
    original_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    final_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    applied_discount_type: Mapped[str] = mapped_column(String(30), default="none")
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)