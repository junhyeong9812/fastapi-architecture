import uuid
from datetime import datetime, UTC

from pygments.styles import default
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import Base

class SubscriptionModel(Base):
    """subscription 테이블."""
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid.uuid4()))
    customer_name: Mapped[str] = mapped_column(String(100))
    tier: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime)