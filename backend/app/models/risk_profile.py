"""
Risk Profile model — per-strategy risk management configuration.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    risk_per_trade_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0, nullable=False)
    daily_loss_limit_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=3.0, nullable=False)
    max_concurrent_trades: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    max_lot_size: Mapped[float] = mapped_column(Numeric(8, 2), default=1.0, nullable=False)
    min_lot_size: Mapped[float] = mapped_column(Numeric(8, 2), default=0.01, nullable=False)
    session_filter: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    advanced_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Relationships
    strategy = relationship("Strategy", back_populates="risk_profile")

    def __repr__(self) -> str:
        return f"<RiskProfile risk={self.risk_per_trade_pct}% strategy={self.strategy_id}>"
