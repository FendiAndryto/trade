"""
Risk Engine — pre-trade validation pipeline.

Validates each incoming trade signal against the user's risk profile
before allowing execution.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DailyLossLimitHit,
    MaxConcurrentTradesExceeded,
)
from app.models.daily_stats import DailyStats
from app.models.mt5_account import MT5Account
from app.models.risk_profile import RiskProfile
from app.models.trade import Trade, TradeStatus
from app.schemas.webhook import WebhookPayload
from app.services.lot_calculator import calculate_lot_from_prices, calculate_lot_size


class RiskCheckResult:
    """Result of a risk validation check."""

    def __init__(self, passed: bool, lot_size: float = 0.0, message: str = ""):
        self.passed = passed
        self.lot_size = lot_size
        self.message = message


async def validate_trade(
    db: AsyncSession,
    user_id: UUID,
    mt5_account: MT5Account,
    risk_profile: RiskProfile,
    payload: WebhookPayload,
) -> RiskCheckResult:
    """
    Run the full risk validation pipeline on an incoming trade signal.

    Checks (in order):
    1. Daily loss limit
    2. Max concurrent trades
    3. Lot size calculation + bounds check

    Returns:
        RiskCheckResult with pass/fail status and calculated lot size.

    Raises:
        DailyLossLimitHit: If daily loss limit has been exceeded.
        MaxConcurrentTradesExceeded: If max concurrent trades reached.
    """

    # Close actions reduce risk — bypass new trade checks
    if payload.action.lower() in ("close", "close_buy", "close_sell"):
        return RiskCheckResult(
            passed=True,
            lot_size=0.0,
            message="Close action approved",
        )

    # --- Check 1: Daily Loss Limit ---
    today = date.today()
    result = await db.execute(
        select(DailyStats).where(
            DailyStats.user_id == user_id,
            DailyStats.mt5_account_id == mt5_account.id,
            DailyStats.trade_date == today,
        )
    )
    daily_stats = result.scalar_one_or_none()

    balance = float(mt5_account.balance) if mt5_account.balance else 0.0
    starting_balance = (
        float(daily_stats.starting_balance)
        if daily_stats and daily_stats.starting_balance
        else balance
    )
    current_pnl = float(daily_stats.total_pnl) if daily_stats else 0.0
    limit_pct = float(risk_profile.daily_loss_limit_pct)

    if starting_balance > 0 and limit_pct > 0:
        loss_pct = (abs(current_pnl) / starting_balance) * 100 if current_pnl < 0 else 0.0
        if loss_pct >= limit_pct:
            raise DailyLossLimitHit(
                current_loss_pct=loss_pct,
                limit_pct=limit_pct,
            )

    # --- Check 2: Max Concurrent Trades ---
    open_count_result = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.user_id == user_id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    open_count = open_count_result.scalar() or 0
    max_trades = risk_profile.max_concurrent_trades

    if open_count >= max_trades:
        raise MaxConcurrentTradesExceeded(
            current_count=open_count,
            max_count=max_trades,
        )

    # --- Check 3: Calculate Lot Size ---
    risk_pct = payload.risk_pct or float(risk_profile.risk_per_trade_pct)
    min_lot = float(risk_profile.min_lot_size)
    max_lot = float(risk_profile.max_lot_size)

    if payload.lot:
        # User provided explicit lot size — clamp to bounds
        lot_size = max(min_lot, min(payload.lot, max_lot))
    elif payload.price and payload.sl:
        # Calculate from entry + SL prices
        lot_size = calculate_lot_from_prices(
            account_balance=balance,
            risk_percent=risk_pct,
            entry_price=payload.price,
            stop_loss_price=payload.sl,
            symbol=payload.symbol,
            min_lot=min_lot,
            max_lot=max_lot,
        )
    else:
        # No SL provided — use a safe default (50 pips for XAUUSD)
        default_sl_pips = 50.0
        lot_size = calculate_lot_size(
            account_balance=balance,
            risk_percent=risk_pct,
            stop_loss_pips=default_sl_pips,
            symbol=payload.symbol,
            min_lot=min_lot,
            max_lot=max_lot,
        )

    return RiskCheckResult(
        passed=True,
        lot_size=lot_size,
        message=f"All checks passed. Lot: {lot_size}, Risk: {risk_pct}%",
    )
