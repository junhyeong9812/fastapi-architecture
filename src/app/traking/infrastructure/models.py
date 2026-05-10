"""events는 JSON 문자열로 저장. PostgreSQL이면 JSONB, SQLite면 TEXT."""

import uuid
from datetime import datetime, UTC
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import Base


class OrderTrackingModel(Base):
    __tablename__ = "order_tracking"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    subscription_tier: Mapped[str] = mapped_column(String(20))
    current_phase: Mapped[str] = mapped_column(String(30))
    events_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON 문자열
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)