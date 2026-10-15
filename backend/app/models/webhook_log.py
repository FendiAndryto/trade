"""
Webhook Log model — audit trail for all incoming webhooks.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WebhookStatus(str, enum.Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[WebhookStatus] = mapped_column(
        Enum(WebhookStatus), default=WebhookStatus.RECEIVED, nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="webhook_logs")

    def __repr__(self) -> str:
        return f"<WebhookLog {self.status.value} strategy={self.strategy_id}>"
