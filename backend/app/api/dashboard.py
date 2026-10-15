"""
Dashboard routes — summary stats, daily stats, equity curve.
"""

import secrets
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.api_token import ApiToken
from app.models.daily_stats import DailyStats
from app.models.mt5_account import MT5Account, MT5Status
from app.models.risk_profile import RiskProfile
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.models.user import User
from app.models.webhook_log import WebhookLog, WebhookStatus
from app.schemas.dashboard import (
    AccountSummary,
    DailyStatsResponse,
    DashboardSummary,
    EquityCurveResponse,
    EquityPoint,
    TradingSummary,
)
from app.schemas.webhook import WebhookLogResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the main dashboard summary — account + trading overview."""
    # Get first MT5 account (for now, single account support)
    result = await db.execute(
        select(MT5Account).where(MT5Account.user_id == current_user.id).limit(1)
    )
    mt5 = result.scalar_one_or_none()

    balance = float(mt5.balance) if mt5 else 0.0
    equity = float(mt5.equity) if mt5 else 0.0

    # Today's stats
    today = date.today()
    today_stats = None
    if mt5:
        result = await db.execute(
            select(DailyStats).where(
                DailyStats.user_id == current_user.id,
                DailyStats.mt5_account_id == mt5.id,
                DailyStats.trade_date == today,
            )
        )
        today_stats = result.scalar_one_or_none()

    # Open trades count
    open_count_result = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    open_count = open_count_result.scalar() or 0

    total_today = today_stats.total_trades if today_stats else 0
    wins_today = today_stats.winning_trades if today_stats else 0
    losses_today = today_stats.losing_trades if today_stats else 0
    pnl_today = float(today_stats.total_pnl) if today_stats else 0.0
    starting = (
        float(today_stats.starting_balance)
        if today_stats and today_stats.starting_balance
        else balance
    )

    return DashboardSummary(
        account=AccountSummary(
            login=mt5.mt5_login if mt5 else None,
            server=mt5.server_name if mt5 else None,
            broker=mt5.broker_name if mt5 else None,
            currency="USD",
            balance=balance,
            equity=equity,
            floating_pnl=equity - balance,
            margin_used=0.0,
            margin_level=None,
            mt5_status=mt5.status.value if mt5 else "disconnected",
        ),
        trading=TradingSummary(
            total_trades_today=total_today,
            winning_trades_today=wins_today,
            losing_trades_today=losses_today,
            pnl_today=pnl_today,
            win_rate_today=(wins_today / total_today * 100) if total_today > 0 else 0.0,
            daily_loss_limit_pct=3.0,  # TODO: from active strategy's risk profile
            daily_loss_used_pct=(abs(pnl_today) / starting * 100)
            if starting > 0 and pnl_today < 0
            else 0.0,
            open_trades_count=open_count,
            max_concurrent_trades=3,  # TODO: from risk profile
        ),
    )


@router.get("/daily-stats", response_model=list[DailyStatsResponse])
async def get_daily_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily trading stats for the last N days."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyStats)
        .where(
            DailyStats.user_id == current_user.id,
            DailyStats.trade_date >= since,
        )
        .order_by(DailyStats.trade_date.desc())
    )
    stats = result.scalars().all()

    return [
        DailyStatsResponse(
            date=str(s.trade_date),
            total_trades=s.total_trades,
            winning_trades=s.winning_trades,
            losing_trades=s.losing_trades,
            total_pnl=float(s.total_pnl),
            max_drawdown=float(s.max_drawdown),
            win_rate=(s.winning_trades / s.total_trades * 100) if s.total_trades > 0 else 0.0,
            daily_limit_hit=s.daily_limit_hit,
        )
        for s in stats
    ]


@router.get("/equity-curve", response_model=EquityCurveResponse)
async def get_equity_curve(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get equity curve data for charting."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyStats)
        .where(
            DailyStats.user_id == current_user.id,
            DailyStats.trade_date >= since,
        )
        .order_by(DailyStats.trade_date.asc())
    )
    stats = result.scalars().all()

    return EquityCurveResponse(
        data=[
            EquityPoint(
                date=str(s.trade_date),
                equity=float(s.ending_balance),
                balance=float(s.starting_balance),
                pnl=float(s.total_pnl),
            )
            for s in stats
        ]
    )


@router.get("/webhooks", response_model=list[WebhookLogResponse])
async def get_recent_webhooks(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent webhook execution logs for the current user's strategies."""
    result = await db.execute(
        select(WebhookLog)
        .join(Strategy, WebhookLog.strategy_id == Strategy.id)
        .where(Strategy.user_id == current_user.id)
        .order_by(WebhookLog.received_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        WebhookLogResponse(
            id=entry.id,
            strategy_id=entry.strategy_id,
            raw_payload=entry.raw_payload,
            status=entry.status.value,
            rejection_reason=entry.rejection_reason,
            received_at=entry.received_at.isoformat(),
            processing_ms=entry.processing_ms,
        )
        for entry in logs
    ]


@router.post("/seed-demo", status_code=status.HTTP_201_CREATED)
async def seed_demo_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed comprehensive demo MT5 account, strategy, trades, and webhook logs for testing."""
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. MT5 Account
    result = await db.execute(
        select(MT5Account).where(MT5Account.user_id == current_user.id).limit(1)
    )
    mt5 = result.scalar_one_or_none()
    if not mt5:
        token = secrets.token_hex(16)
        mt5 = MT5Account(
            user_id=current_user.id,
            mt5_login=10928374,
            server_name="MetaQuotes-Demo",
            broker_name="MetaQuotes Software Corp.",
            status=MT5Status.CONNECTED,
            balance=10245.30,
            equity=10312.50,
            agent_token_hash=sha256(token.encode()).hexdigest(),
            last_sync_at=now,
        )
        db.add(mt5)
        await db.flush()

    # 2. Strategy & Risk Profile
    result = await db.execute(select(Strategy).where(Strategy.user_id == current_user.id).limit(1))
    strategy = result.scalar_one_or_none()
    if not strategy:
        strategy = Strategy(
            user_id=current_user.id,
            name="Gold Scalper Pro XAUUSD",
            description="Automated 15m pullback and breakout strategy from TradingView",
            is_active=True,
        )
        db.add(strategy)
        await db.flush()

        risk = RiskProfile(
            strategy_id=strategy.id,
            risk_per_trade_pct=1.0,
            daily_loss_limit_pct=3.0,
            max_concurrent_trades=3,
            max_lot_size=1.0,
            min_lot_size=0.01,
        )
        db.add(risk)

        # Ensure API token
        raw_tok = secrets.token_urlsafe(32)
        api_token = ApiToken(
            user_id=current_user.id,
            token_hash=sha256(raw_tok.encode()).hexdigest(),
            label="TradingView Webhook Token",
        )
        db.add(api_token)
        await db.flush()

    # 3. Daily Stats (14-day equity history)
    existing_stats = await db.execute(
        select(DailyStats).where(
            DailyStats.user_id == current_user.id,
            DailyStats.mt5_account_id == mt5.id,
        )
    )
    existing_days = {s.trade_date for s in existing_stats.scalars().all()}

    curve_data = [
        (-13, 10000.00, 10035.00, 35.00, 2, 2, 0, 0.15),
        (-12, 10035.00, 10082.50, 47.50, 3, 2, 1, 0.22),
        (-11, 10082.50, 10060.00, -22.50, 2, 1, 1, 0.40),
        (-10, 10060.00, 10115.00, 55.00, 4, 3, 1, 0.18),
        (-9, 10115.00, 10140.20, 25.20, 2, 2, 0, 0.10),
        (-8, 10140.20, 10110.00, -30.20, 3, 1, 2, 0.55),
        (-7, 10110.00, 10178.40, 68.40, 4, 3, 1, 0.20),
        (-6, 10178.40, 10210.00, 31.60, 2, 2, 0, 0.12),
        (-5, 10210.00, 10185.00, -25.00, 3, 1, 2, 0.48),
        (-4, 10185.00, 10240.00, 55.00, 3, 3, 0, 0.15),
        (-3, 10240.00, 10275.50, 35.50, 2, 2, 0, 0.10),
        (-2, 10275.50, 10250.00, -25.50, 2, 1, 1, 0.35),
        (-1, 10250.00, 10300.00, 50.00, 3, 2, 1, 0.20),
        (0, 10300.00, 10312.50, 12.50, 4, 3, 1, 0.18),
    ]

    for day_offset, start_bal, end_bal, pnl, total_t, win_t, loss_t, dd in curve_data:
        target_date = today + timedelta(days=day_offset)
        if target_date not in existing_days:
            db.add(
                DailyStats(
                    user_id=current_user.id,
                    mt5_account_id=mt5.id,
                    trade_date=target_date,
                    total_trades=total_t,
                    winning_trades=win_t,
                    losing_trades=loss_t,
                    total_pnl=pnl,
                    max_drawdown=dd,
                    starting_balance=start_bal,
                    ending_balance=end_bal,
                    daily_limit_hit=False,
                )
            )

    # 4. Trades
    trade_check = await db.execute(select(Trade).where(Trade.user_id == current_user.id).limit(1))
    if not trade_check.scalar_one_or_none():
        t1 = Trade(
            user_id=current_user.id,
            strategy_id=strategy.id,
            mt5_account_id=mt5.id,
            mt5_ticket=4829104,
            symbol="XAUUSD",
            direction=TradeDirection.BUY,
            lot_size=0.10,
            entry_price=2648.50,
            stop_loss=2642.00,
            take_profit=2665.00,
            status=TradeStatus.OPEN,
            realized_pnl=0.0,
            comment="TV: Trend pullback entry",
            opened_at=now - timedelta(minutes=42),
        )
        t2 = Trade(
            user_id=current_user.id,
            strategy_id=strategy.id,
            mt5_account_id=mt5.id,
            mt5_ticket=4829105,
            symbol="EURUSD",
            direction=TradeDirection.SELL,
            lot_size=0.20,
            entry_price=1.08920,
            stop_loss=1.09150,
            take_profit=1.08400,
            status=TradeStatus.OPEN,
            realized_pnl=0.0,
            comment="TV: Bearish pin bar",
            opened_at=now - timedelta(minutes=15),
        )
        t3 = Trade(
            user_id=current_user.id,
            strategy_id=strategy.id,
            mt5_account_id=mt5.id,
            mt5_ticket=4828901,
            symbol="XAUUSD",
            direction=TradeDirection.BUY,
            lot_size=0.10,
            entry_price=2638.10,
            close_price=2647.30,
            stop_loss=2632.00,
            take_profit=2648.00,
            status=TradeStatus.CLOSED,
            realized_pnl=92.00,
            comment="TP hit +920 pts",
            opened_at=now - timedelta(hours=3),
            closed_at=now - timedelta(hours=1),
        )
        db.add_all([t1, t2, t3])

    # 5. Webhook Logs
    wh_check = await db.execute(
        select(WebhookLog).where(WebhookLog.strategy_id == strategy.id).limit(1)
    )
    if not wh_check.scalar_one_or_none():
        w1 = WebhookLog(
            strategy_id=strategy.id,
            raw_payload={
                "action": "buy",
                "symbol": "XAUUSD",
                "sl": 2642.0,
                "tp": 2665.0,
                "time": "11:02:14",
            },
            status=WebhookStatus.EXECUTED,
            processing_ms=38,
            received_at=now - timedelta(minutes=42),
        )
        w2 = WebhookLog(
            strategy_id=strategy.id,
            raw_payload={
                "action": "sell",
                "symbol": "EURUSD",
                "sl": 1.0915,
                "tp": 1.0840,
                "time": "11:29:05",
            },
            status=WebhookStatus.EXECUTED,
            processing_ms=45,
            received_at=now - timedelta(minutes=15),
        )
        w3 = WebhookLog(
            strategy_id=strategy.id,
            raw_payload={"action": "buy", "symbol": "BTCUSD", "sl": 66500.0, "time": "11:35:10"},
            status=WebhookStatus.REJECTED,
            rejection_reason="Symbol BTCUSD not allowed in risk profile whitelist",
            processing_ms=12,
            received_at=now - timedelta(minutes=8),
        )
        db.add_all([w1, w2, w3])

    await db.flush()
    return {"message": "Demo data successfully seeded!", "status": "success"}
