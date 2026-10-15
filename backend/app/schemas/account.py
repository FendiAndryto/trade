"""
Schemas for MT5 Account management and No-Code pairing.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MT5AccountCreate(BaseModel):
    mt5_login: int = Field(..., description="MT5 Account Number / Login ID")
    server_name: str = Field(..., description="Broker Server Name (e.g. Exness-Real10)")
    broker_name: str = Field(default="", description="Broker Company Name")


class MT5AccountResponse(BaseModel):
    id: UUID
    mt5_login: int
    server_name: str
    broker_name: str
    status: str
    balance: float
    equity: float
    pairing_code: str | None = None
    last_sync_at: datetime | None = None

    model_config = {"from_attributes": True}


class MT5PairRequest(BaseModel):
    pairing_code: str = Field(..., description="6-character pairing code shown on web")
    login: int | None = Field(default=None)
    server: str | None = Field(default=None)
    broker: str | None = Field(default=None)
    balance: float | None = Field(default=0.0)
    equity: float | None = Field(default=0.0)


class MT5PairResponse(BaseModel):
    status: str
    message: str
    account_id: str | None = None
    agent_token: str | None = None


class MT5AgentEventRequest(BaseModel):
    agent_token: str = Field(default="")
    event: str = Field(..., description="deal_add, order_add, tick, heartbeat, candles")
    data: dict = Field(default_factory=dict)
