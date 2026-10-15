"""
Autonomous Strategy Runner — 24/7 Autopilot Trading Engine.
Monitors market candles and executes algorithmic entries automatically without external alerts.
"""

import asyncio
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models.mt5_account import MT5Account
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.services.candle_service import get_or_generate_candles
from app.services.exit_manager import evaluate_exit_conditions
from app.services.news_filter import is_news_blackout
from app.services.strategy_engine import evaluate_built_in_strategy
from app.ws.manager import ws_manager

_last_executed_bar: dict[str, int] = {}
_runner_task: asyncio.Task | None = None


async def run_autonomous_strategy_engine():
    """Background loop that continuously runs autonomous strategies."""
    print("[*] 🤖 Autonomous Strategy Runner (Autopilot) started.")
    await asyncio.sleep(5)  # Wait for startup

    while True:
        try:
            await asyncio.sleep(15)  # Scan market every 15s

            async with async_session_factory() as db:
                # 1. Fetch all active strategies
                res = await db.execute(
                    select(Strategy)
                    .options(selectinload(Strategy.risk_profile))
                    .where(Strategy.is_active == True)  # noqa: E712
                )
                active_strategies = res.scalars().all()
                if not active_strategies:
                    continue

                for strat in active_strategies:
                    symbol = "XAUUSD"
                    strat_type = "ema_cross"

                    # Check news filter
                    if is_news_blackout(symbol):
                        continue

                    # Fetch candles
                    candles = get_or_generate_candles(symbol, count=120)
                    if not candles or len(candles) < 30:
                        continue

                    current_bar_time = candles[-1]["time"]
                    debounce_key = f"{strat.id}_{symbol}"
                    if _last_executed_bar.get(debounce_key) == current_bar_time:
                        continue

                    # Evaluate strategy signals
                    signal = evaluate_built_in_strategy(strat_type, candles)
                    if not signal:
                        continue

                    # Check if user already has an active trade for this symbol
                    open_trades_res = await db.execute(
                        select(Trade).where(
                            Trade.user_id == strat.user_id,
                            Trade.symbol == symbol,
                            Trade.status == TradeStatus.OPEN,
                        )
                    )
                    open_trades = open_trades_res.scalars().all()
                    max_trades = strat.risk_profile.max_concurrent_trades if strat.risk_profile else 3
                    if len(open_trades) >= max_trades:
                        continue

                    # Avoid same direction duplicate
                    direction_enum = TradeDirection.BUY if signal == "buy" else TradeDirection.SELL
                    if any(t.direction == direction_enum for t in open_trades):
                        continue

                    # Find user's MT5 account
                    acc_res = await db.execute(
                        select(MT5Account).where(MT5Account.user_id == strat.user_id).limit(1)
                    )
                    mt5_acc = acc_res.scalar_one_or_none()

                    curr_price = float(candles[-1]["close"])
                    lot_size = float(strat.risk_profile.min_lot_size) if strat.risk_profile else 0.01

                    # Auto SL/TP
                    digits = 2 if symbol in ("XAUUSD", "BTCUSD") else 5
                    pip_unit = 0.10 if symbol == "XAUUSD" else 1.0
                    sl_dist = 40 * pip_unit
                    tp_dist = 80 * pip_unit

                    if direction_enum == TradeDirection.BUY:
                        sl = round(curr_price - sl_dist, digits)
                        tp = round(curr_price + tp_dist, digits)
                    else:
                        sl = round(curr_price + sl_dist, digits)
                        tp = round(curr_price - tp_dist, digits)

                    now = datetime.now(timezone.utc)
                    trade = Trade(
                        user_id=strat.user_id,
                        strategy_id=strat.id,
                        mt5_account_id=mt5_acc.id if mt5_acc else None,
                        symbol=symbol,
                        direction=direction_enum,
                        lot_size=lot_size,
                        entry_price=curr_price,
                        stop_loss=sl,
                        take_profit=tp,
                        status=TradeStatus.OPEN,
                        comment=f"AutoBot {strat_type.upper()}",
                        opened_at=now,
                    )
                    db.add(trade)
                    await db.commit()
                    await db.refresh(trade)

                    _last_executed_bar[debounce_key] = current_bar_time

                    # Dispatch to connected agent
                    if mt5_acc and ws_manager.is_agent_connected(mt5_acc.id):
                        await ws_manager.send_to_agent(
                            mt5_acc.id,
                            "execute_order",
                            {
                                "trade_id": str(trade.id),
                                "symbol": symbol,
                                "direction": direction_enum.value,
                                "lot": lot_size,
                                "sl": sl,
                                "tp": tp,
                                "comment": trade.comment,
                            },
                        )

                    # Broadcast trade to user dashboard
                    trade_payload = {
                        "id": str(trade.id),
                        "symbol": symbol,
                        "direction": direction_enum.value,
                        "lot": lot_size,
                        "entry_price": curr_price,
                        "sl": sl,
                        "tp": tp,
                        "pnl": 0.0,
                        "comment": trade.comment,
                    }
                    await ws_manager.send_to_user(strat.user_id, "trade.opened", trade_payload)

                    # Send toast to user's screen
                    await ws_manager.send_to_user(
                        strat.user_id,
                        "toast",
                        {
                            "type": "success",
                            "title": "🤖 Robot Autopilot Entry",
                            "message": f"Sinyal {direction_enum.value.upper()} {symbol} terdeteksi! Posisi otomatis dibuka pada {curr_price}.",
                        },
                    )
                    print(f"[*] 🤖 [Autopilot] Auto {direction_enum.value.upper()} executed for user {strat.user_id} on {symbol}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[!] Autonomous runner loop error: {e}")
            await asyncio.sleep(5)
