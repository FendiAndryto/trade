"""
Webhook schemas — TradingView alert payload validation.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """Incoming webhook payload from TradingView."""

    action: str = Field(
        ...,
        pattern="^(buy|sell|close|close_buy|close_sell)$",
        description="Trade action: buy, sell, close, close_buy, close_sell",
    )
    symbol: str = Field(default="XAUUSD", max_length=20, description="Trading symbol, e.g. XAUUSD")
    price: float | None = Field(
        default=None, ge=0, description="Entry price (optional, uses market price if omitted)"
    )
    sl: float | None = Field(default=None, ge=0, description="Stop loss price")
    tp: float | None = Field(default=None, ge=0, description="Take profit price")
    lot: float | None = Field(
        default=None, ge=0.01, le=100, description="Lot size (overrides auto-calc if provided)"
    )
    risk_pct: float | None = Field(
        default=None, ge=0.1, le=50, description="Risk % override for this trade"
    )
    comment: str = Field(default="", max_length=500, description="Trade comment / label")
    magic: int | None = Field(default=None, description="Magic number for MT5")


class WebhookResponse(BaseModel):
    status: str
    webhook_id: UUID
    message: str


class WebhookLogResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    raw_payload: dict
    status: str
    rejection_reason: str | None
    received_at: str
    processing_ms: int | None

    model_config = {"from_attributes": True}
