"""
Daily Stats model — aggregated daily trading statistics for risk tracking.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DailyStats(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "mt5_account_id", "trade_date", name="uq_daily_stats"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mt5_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mt5_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    starting_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    ending_balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    daily_limit_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="daily_stats")
    mt5_account = relationship("MT5Account", back_populates="daily_stats")

    def __repr__(self) -> str:
        return f"<DailyStats {self.trade_date} pnl={self.total_pnl}>"
