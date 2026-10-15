"""
Trade model — individual trade records.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TradeDirection(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mt5_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mt5_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mt5_ticket: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[TradeDirection] = mapped_column(Enum(TradeDirection), nullable=False)
    lot_size: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Numeric(12, 5), nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 5), nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Numeric(12, 5), nullable=True)
    close_price: Mapped[float | None] = mapped_column(Numeric(12, 5), nullable=True)
    status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus), default=TradeStatus.PENDING, nullable=False
    )
    realized_pnl: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    commission: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    swap: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    comment: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    mt5_account = relationship("MT5Account", back_populates="trades")

    def __repr__(self) -> str:
        return f"<Trade {self.symbol} {self.direction.value} {self.lot_size} lots>"
