"""
Dashboard schemas — summary stats and chart data.
"""

from pydantic import BaseModel


class AccountSummary(BaseModel):
    login: int | None = None
    server: str | None = None
    broker: str | None = None
    currency: str | None = "USD"
    balance: float
    equity: float
    floating_pnl: float
    margin_used: float
    margin_level: float | None
    mt5_status: str


class TradingSummary(BaseModel):
    total_trades_today: int
    winning_trades_today: int
    losing_trades_today: int
    pnl_today: float
    win_rate_today: float
    daily_loss_limit_pct: float
    daily_loss_used_pct: float
    open_trades_count: int
    max_concurrent_trades: int


class DashboardSummary(BaseModel):
    account: AccountSummary
    trading: TradingSummary


class EquityPoint(BaseModel):
    date: str
    equity: float
    balance: float
    pnl: float


class EquityCurveResponse(BaseModel):
    data: list[EquityPoint]


class DailyStatsResponse(BaseModel):
    date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    win_rate: float
    daily_limit_hit: bool

    model_config = {"from_attributes": True}
