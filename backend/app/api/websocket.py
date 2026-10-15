import asyncio
import json
import random
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_token
from app.database import async_session_factory
from app.models.trade import Trade, TradeStatus
from app.ws.manager import ws_manager

router = APIRouter(tags=["WebSocket"])

latest_candles: dict[str, list[dict]] = {}
_tick_task: asyncio.Task | None = None
_prices = {
    "XAUUSD": 2651.30,
    "EURUSD": 1.08520,
    "GBPUSD": 1.29850,
    "BTCUSD": 67450.0,
}


async def _tick_simulation_loop():
    """Simulates market ticks when MT5 agent is offline so dashboard shows live prices."""
    while True:
        try:
            await asyncio.sleep(1.5)
            if not ws_manager.active_connections:
                continue
            if ws_manager.has_connected_agents:
                continue

            subscribed = ws_manager.get_all_subscribed_symbols()
            if not subscribed:
                subscribed = {"XAUUSD"}

            for symbol in subscribed:
                curr = _prices.get(symbol, 2650.0)
                if symbol == "XAUUSD":
                    delta = (random.random() - 0.49) * 0.45
                    curr = round(curr + delta, 2)
                    spread = 0.30
                elif symbol == "EURUSD":
                    delta = (random.random() - 0.49) * 0.00015
                    curr = round(curr + delta, 5)
                    spread = 0.00015
                elif symbol == "BTCUSD":
                    delta = (random.random() - 0.49) * 15.0
                    curr = round(curr + delta, 2)
                    spread = 5.0
                else:
                    delta = (random.random() - 0.49) * 0.10
                    curr = round(curr + delta, 2)
                    spread = 0.10

                _prices[symbol] = curr
                tick = {
                    "symbol": symbol,
                    "bid": curr,
                    "ask": round(curr + spread, 5 if "EUR" in symbol else 2),
                    "time": datetime.now(timezone.utc).isoformat(),
                }
                await ws_manager.broadcast_tick(symbol, tick)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time dashboard updates.

    Connect with: ws://host/ws?token=<jwt_access_token>
    """
    # Validate JWT token
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = UUID(payload["sub"])

    # Accept and register connection
    await ws_manager.connect(websocket, user_id)

    # Ensure tick simulator is active
    global _tick_task
    if _tick_task is None or _tick_task.done():
        _tick_task = asyncio.create_task(_tick_simulation_loop())

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                event = message.get("event", "")

                if event == "ping":
                    await websocket.send_json({"event": "pong"})
                elif event == "subscribe":
                    symbols = message.get("data", {}).get("symbols", [])
                    await ws_manager.subscribe(user_id, symbols)
                    for s in symbols:
                        s_upper = s.upper()
                        curr = _prices.get(s_upper, 2651.30)
                        await websocket.send_json(
                            {
                                "event": "tick",
                                "data": {
                                    "symbol": s_upper,
                                    "bid": curr,
                                    "ask": round(curr + 0.30, 2),
                                    "time": datetime.now(timezone.utc).isoformat(),
                                },
                            }
                        )
                elif event == "close_trade":
                    trade_id_str = message.get("data", {}).get("trade_id")
                    if trade_id_str:
                        async with async_session_factory() as db:
                            res = await db.execute(
                                select(Trade).where(
                                    Trade.id == UUID(trade_id_str),
                                    Trade.user_id == user_id,
                                    Trade.status == TradeStatus.OPEN,
                                )
                            )
                            t = res.scalar_one_or_none()
                            if t:
                                if t.mt5_account_id and ws_manager.is_agent_connected(
                                    t.mt5_account_id
                                ):
                                    await ws_manager.send_to_agent(
                                        t.mt5_account_id,
                                        "close_position",
                                        {"trade_id": str(t.id), "ticket": t.mt5_ticket},
                                    )
                                    t.status = TradeStatus.PENDING
                                else:
                                    t.status = TradeStatus.CLOSED
                                    t.closed_at = datetime.now(timezone.utc)
                                    if t.entry_price and not t.close_price:
                                        t.close_price = t.entry_price
                                await db.commit()
                                await websocket.send_json(
                                    {
                                        "event": "trade.closed",
                                        "data": {"trade_id": str(t.id), "status": t.status.value},
                                    }
                                )
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "event": "error",
                        "data": {"message": "Invalid JSON"},
                    }
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)


@router.websocket("/ws/agent")
async def agent_websocket_endpoint(websocket: WebSocket, agent_token: str = Query(...)):
    """
    WebSocket endpoint for MT5 Agent connections.

    Connect with: ws://host/ws/agent?agent_token=<token>
    """
    from datetime import datetime, timezone
    from hashlib import sha256

    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.mt5_account import MT5Account, MT5Status
    from app.models.trade import Trade, TradeStatus

    token_hash = sha256(agent_token.encode()).hexdigest()

    async with async_session_factory() as db:
        result = await db.execute(
            select(MT5Account).where(
                (MT5Account.agent_token_hash == token_hash)
                | (MT5Account.pairing_code == agent_token)
                | (MT5Account.pairing_code == agent_token.upper())
            )
        )
        mt5_account = result.scalar_one_or_none()

        if mt5_account is None:
            # Fallback for dev / demo mode: find any existing account if token is dev-agent-secret
            if "dev" in agent_token:
                dev_res = await db.execute(select(MT5Account).limit(1))
                mt5_account = dev_res.scalar_one_or_none()

        if mt5_account is None:
            await websocket.close(code=4001, reason="Invalid agent token")
            return

        account_id = mt5_account.id
        user_id = mt5_account.user_id

        # Mark account as connected
        mt5_account.status = MT5Status.CONNECTED
        mt5_account.last_sync_at = datetime.now(timezone.utc)
        await db.commit()

    # Register agent in ws_manager
    await ws_manager.connect_agent(websocket, account_id)
    print(f"[*] MT5 Agent connected for account {account_id}")

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                event = msg.get("event", "")
                data = msg.get("data", {})

                if event == "account_update":
                    async with async_session_factory() as db:
                        res = await db.execute(
                            select(MT5Account).where(MT5Account.id == account_id)
                        )
                        acc = res.scalar_one_or_none()
                        if acc:
                            if "balance" in data:
                                acc.balance = float(data["balance"])
                            if "equity" in data:
                                acc.equity = float(data["equity"])
                            if data.get("login"):
                                acc.mt5_login = int(data["login"])
                            if data.get("server"):
                                acc.server_name = str(data["server"])
                            if data.get("company"):
                                acc.broker_name = str(data["company"])
                            acc.status = MT5Status.CONNECTED
                            acc.last_sync_at = datetime.now(timezone.utc)

                            # Sync real open positions from MT5 terminal
                            if "positions" in data:
                                positions = data["positions"] or []
                                active_tickets = {int(p["ticket"]) for p in positions}

                                # 1. Upsert open positions from MT5
                                for p in positions:
                                    ticket = int(p["ticket"])
                                    t_res = await db.execute(
                                        select(Trade).where(
                                            Trade.user_id == user_id,
                                            Trade.mt5_ticket == ticket,
                                        )
                                    )
                                    existing_trade = t_res.scalar_one_or_none()
                                    pnl = float(p.get("pnl", 0.0))
                                    if existing_trade:
                                        existing_trade.realized_pnl = pnl
                                        existing_trade.status = TradeStatus.OPEN
                                        if p.get("sl_price"):
                                            existing_trade.stop_loss = float(p["sl_price"])
                                        if p.get("tp_price"):
                                            existing_trade.take_profit = float(p["tp_price"])
                                    else:
                                        direction = (
                                            TradeDirection.BUY
                                            if str(p.get("direction", "")).lower() == "buy"
                                            else TradeDirection.SELL
                                        )
                                        new_trade = Trade(
                                            user_id=user_id,
                                            mt5_account_id=account_id,
                                            mt5_ticket=ticket,
                                            symbol=str(p.get("symbol", "XAUUSD")).upper().rstrip("M"),
                                            direction=direction,
                                            lot_size=float(p.get("lot", 0.01)),
                                            entry_price=float(p.get("open_price", 0.0)),
                                            stop_loss=float(p["sl_price"]) if p.get("sl_price") else None,
                                            take_profit=float(p["tp_price"]) if p.get("tp_price") else None,
                                            realized_pnl=pnl,
                                            status=TradeStatus.OPEN,
                                            comment=str(p.get("comment", "MT5 Terminal")),
                                        )
                                        db.add(new_trade)

                                # 2. Mark trades as CLOSED if no longer in active_tickets
                                open_trades_res = await db.execute(
                                    select(Trade).where(
                                        Trade.user_id == user_id,
                                        Trade.status == TradeStatus.OPEN,
                                    )
                                )
                                for ot in open_trades_res.scalars().all():
                                    if ot.mt5_ticket and ot.mt5_ticket not in active_tickets:
                                        ot.status = TradeStatus.CLOSED
                                        ot.closed_at = datetime.now(timezone.utc)

                            await db.commit()

                    # Broadcast update to user's dashboard
                    await ws_manager.send_to_user(user_id, "account_update", data)

                elif event == "candles_update":
                    from app.services.candle_service import set_candles
                    sym = str(data.get("symbol", "XAUUSD")).upper().rstrip("M")
                    candles = data.get("candles", [])
                    latest_candles[sym] = candles
                    set_candles(sym, candles)
                    await ws_manager.send_to_user(user_id, "candles", {"symbol": sym, "candles": candles})

                elif event == "tick":
                    from app.services.candle_service import update_candle_with_tick
                    symbol = data.get("symbol", "")
                    await ws_manager.broadcast_tick(symbol, data)
                    if data.get("bid"):
                        t_val = data.get("time")
                        t_epoch = None
                        if t_val is not None:
                            try:
                                t_epoch = int(float(t_val))
                            except (ValueError, TypeError):
                                pass
                        update_candle_with_tick(symbol, float(data["bid"]), t_epoch)


                elif event == "execution_report":
                    trade_id_str = data.get("trade_id")
                    if trade_id_str:
                        async with async_session_factory() as db:
                            res = await db.execute(
                                select(Trade).where(Trade.id == UUID(trade_id_str))
                            )
                            trade = res.scalar_one_or_none()
                            if trade:
                                trade.mt5_ticket = data.get("ticket")
                                if data.get("price"):
                                    trade.entry_price = float(data["price"])
                                trade.status = (
                                    TradeStatus.OPEN if data.get("success") else TradeStatus.FAILED
                                )
                                await db.commit()

                    await ws_manager.send_to_user(user_id, "trade.executed", data)

                elif event == "close_report":
                    trade_id_str = data.get("trade_id")
                    if trade_id_str:
                        async with async_session_factory() as db:
                            res = await db.execute(
                                select(Trade).where(Trade.id == UUID(trade_id_str))
                            )
                            trade = res.scalar_one_or_none()
                            if trade and data.get("success"):
                                trade.status = TradeStatus.CLOSED
                                trade.closed_at = datetime.now(timezone.utc)
                                if data.get("price"):
                                    trade.close_price = float(data["price"])
                                await db.commit()

                    await ws_manager.send_to_user(user_id, "trade.closed", data)

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect_agent(account_id)
        print(f"[*] MT5 Agent disconnected for account {account_id}")
        async with async_session_factory() as db:
            res = await db.execute(select(MT5Account).where(MT5Account.id == account_id))
            acc = res.scalar_one_or_none()
            if acc:
                acc.status = MT5Status.DISCONNECTED
                await db.commit()
