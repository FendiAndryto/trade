"""
Strategy & Risk Profile schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Risk Profile ---
class RiskProfileSchema(BaseModel):
    risk_per_trade_pct: float = Field(default=1.0, ge=0.1, le=50.0)
    daily_loss_limit_pct: float = Field(default=3.0, ge=0.5, le=100.0)
    max_concurrent_trades: int = Field(default=3, ge=1, le=50)
    max_lot_size: float = Field(default=1.0, ge=0.01, le=100.0)
    min_lot_size: float = Field(default=0.01, ge=0.01, le=10.0)
    session_filter: dict | None = None
    advanced_rules: dict | None = None

    model_config = {"from_attributes": True}


# --- Strategy ---
class StrategyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    risk_profile: RiskProfileSchema = Field(default_factory=RiskProfileSchema)


class StrategyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class StrategyResponse(BaseModel):
    id: UUID
    name: str
    description: str
    is_active: bool
    webhook_url: str = ""
    risk_profile: RiskProfileSchema | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
