"""
Trade schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TradeResponse(BaseModel):
    id: UUID
    symbol: str
    direction: str
    lot_size: float
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    close_price: float | None
    status: str
    realized_pnl: float
    commission: float
    swap: float
    comment: str
    opened_at: datetime
    closed_at: datetime | None
    strategy_id: UUID | None
    mt5_ticket: int | None

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    per_page: int


class ManualTradeCreate(BaseModel):
    symbol: str = "XAUUSD"
    direction: str = "buy"  # "buy" or "sell"
    lot_size: float = 0.01
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str = "TradeGear Manual"


class TradeModifyRequest(BaseModel):
    stop_loss: float | None = None
    take_profit: float | None = None

