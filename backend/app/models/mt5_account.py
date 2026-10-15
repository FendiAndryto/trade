"""
MT5 Account model — tracks connected MetaTrader 5 accounts.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MT5Status(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MT5Account(Base):
    __tablename__ = "mt5_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mt5_login: Mapped[int] = mapped_column(BigInteger, nullable=False)
    server_name: Mapped[str] = mapped_column(String(200), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[MT5Status] = mapped_column(
        Enum(MT5Status), default=MT5Status.DISCONNECTED, nullable=False
    )
    balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    equity: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    agent_token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="mt5_accounts")
    trades = relationship("Trade", back_populates="mt5_account", cascade="all, delete-orphan")
    daily_stats = relationship(
        "DailyStats", back_populates="mt5_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MT5Account {self.mt5_login}@{self.server_name}>"
