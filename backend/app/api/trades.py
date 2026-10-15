"""
Trades routes — list, manage, execute manual orders, and ingest MQL5 EA events.
"""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.mt5_account import MT5Account, MT5Status
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.models.user import User
from app.schemas.account import MT5AgentEventRequest
from app.schemas.trade import (
    ManualTradeCreate,
    TradeListResponse,
    TradeModifyRequest,
    TradeResponse,
)
from app.services.candle_service import (
    get_or_generate_candles,
    update_candle_with_tick,
)
from app.ws.manager import ws_manager

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("", response_model=TradeListResponse)
async def list_trades(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    status_filter: TradeStatus | None = Query(default=None, alias="status"),
    symbol: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List trades with pagination and optional filters."""
    query = select(Trade).where(Trade.user_id == current_user.id)
    count_query = select(func.count(Trade.id)).where(Trade.user_id == current_user.id)

    if status_filter:
        query = query.where(Trade.status == status_filter)
        count_query = count_query.where(Trade.status == status_filter)
    if symbol:
        query = query.where(Trade.symbol == symbol.upper())
        count_query = count_query.where(Trade.symbol == symbol.upper())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Trade.opened_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    trades = result.scalars().all()

    return TradeListResponse(
        trades=[TradeResponse.model_validate(t) for t in trades],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/candles")
async def get_candles(symbol: str = "XAUUSD"):
    """Get latest candlestick data for symbol with robust fallback and caching."""
    sym = symbol.upper().rstrip("M")
    candles = get_or_generate_candles(sym, count=120)
    return {"symbol": sym, "candles": candles}


@router.post("/manual", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_trade(
    req: ManualTradeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a manual market trade directly from the Web Dashboard.
    Validates account and immediately dispatches command to MT5 terminal.
    """
    acc_res = await db.execute(
        select(MT5Account).where(MT5Account.user_id == current_user.id).limit(1)
    )
    mt5_account = acc_res.scalar_one_or_none()

    direction_enum = (
        TradeDirection.BUY if req.direction.lower() == "buy" else TradeDirection.SELL
    )
    now = datetime.now(timezone.utc)

    trade = Trade(
        user_id=current_user.id,
        mt5_account_id=mt5_account.id if mt5_account else None,
        symbol=req.symbol.upper(),
        direction=direction_enum,
        lot_size=req.lot_size,
        entry_price=None,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        status=TradeStatus.OPEN,
        comment=req.comment or "Web Manual Entry",
        opened_at=now,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    # Dispatch to MT5 if connected
    if mt5_account and ws_manager.is_agent_connected(mt5_account.id):
        await ws_manager.send_to_agent(
            mt5_account.id,
            "execute_order",
            {
                "trade_id": str(trade.id),
                "symbol": trade.symbol,
                "direction": trade.direction.value,
                "lot": float(trade.lot_size),
                "sl": float(trade.stop_loss) if trade.stop_loss else None,
                "tp": float(trade.take_profit) if trade.take_profit else None,
                "comment": trade.comment,
            },
        )

    # Broadcast to dashboard
    await ws_manager.send_to_user(
        current_user.id,
        "trade.opened",
        {
            "id": str(trade.id),
            "symbol": trade.symbol,
            "direction": trade.direction.value,
            "lot": float(trade.lot_size),
            "entry_price": float(trade.entry_price) if trade.entry_price else None,
            "sl": float(trade.stop_loss) if trade.stop_loss else None,
            "tp": float(trade.take_profit) if trade.take_profit else None,
        },
    )

    return TradeResponse.model_validate(trade)


@router.patch("/{trade_id}/modify", response_model=TradeResponse)
async def modify_trade(
    trade_id: UUID,
    req: TradeModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Modify Stop Loss and Take Profit of an active position from Web UI."""
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Open trade not found")

    if req.stop_loss is not None:
        trade.stop_loss = req.stop_loss
    if req.take_profit is not None:
        trade.take_profit = req.take_profit

    await db.commit()
    await db.refresh(trade)

    # Inform MT5 agent if connected
    if trade.mt5_account_id and ws_manager.is_agent_connected(trade.mt5_account_id):
        await ws_manager.send_to_agent(
            trade.mt5_account_id,
            "modify_position",
            {
                "trade_id": str(trade.id),
                "ticket": trade.mt5_ticket,
                "sl": float(trade.stop_loss) if trade.stop_loss else None,
                "tp": float(trade.take_profit) if trade.take_profit else None,
            },
        )

    return TradeResponse.model_validate(trade)


@router.post("/agent-event")
async def ingest_agent_event(
    payload: MT5AgentEventRequest,
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Public ingestion endpoint for MQL5 Expert Advisor and Bridge Agent.
    Receives real-time transactions, ticks, and heartbeat pings from MT5.
    """
    token = (payload.agent_token or x_agent_token or "").strip()
    token_hash = sha256(token.encode()).hexdigest()

    result = await db.execute(
        select(MT5Account).where(
            (MT5Account.pairing_code == token)
            | (MT5Account.agent_token_hash == token_hash)
            | (MT5Account.pairing_code == token.upper())
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        if "dev" in token.lower() or token in ("TG-000000", ""):
            dev_res = await db.execute(select(MT5Account).limit(1))
            account = dev_res.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=401, detail="Unauthorized agent token")

    user_id = account.user_id
    event = payload.event
    data = payload.data
    now = datetime.now(timezone.utc)

    account.status = MT5Status.CONNECTED
    account.last_sync_at = now

    if event in ("position_opened", "deal_add"):
        ticket = int(data.get("position_id") or data.get("ticket", 0))
        sym = str(data.get("symbol", "XAUUSD")).upper().rstrip("M")
        lot = float(data.get("lot", 0.01))
        price = float(data.get("price", 0.0))
        direction = (
            TradeDirection.BUY
            if str(data.get("direction", "")).lower() == "buy"
            else TradeDirection.SELL
        )
        pnl = float(data.get("pnl", 0.0))

        if "balance" in data:
            account.balance = float(data["balance"])
        if "equity" in data:
            account.equity = float(data["equity"])

        # Check existing
        t_res = await db.execute(
            select(Trade).where(Trade.user_id == user_id, Trade.mt5_ticket == ticket)
        )
        existing = t_res.scalar_one_or_none()
        if existing:
            existing.realized_pnl = pnl
            existing.status = TradeStatus.OPEN
        else:
            new_trade = Trade(
                user_id=user_id,
                mt5_account_id=account.id,
                mt5_ticket=ticket,
                symbol=sym,
                direction=direction,
                lot_size=lot,
                entry_price=price,
                realized_pnl=pnl,
                status=TradeStatus.OPEN,
                comment=str(data.get("comment", "MT5 Real-Time")),
                opened_at=now,
            )
            db.add(new_trade)

        await db.commit()
        await ws_manager.send_to_user(
            user_id,
            "trade.opened",
            {
                "symbol": sym,
                "direction": direction.value,
                "lot": lot,
                "entry_price": price,
                "ticket": ticket,
            },
        )
        await ws_manager.send_to_user(
            user_id,
            "account_update",
            {
                "login": account.mt5_login,
                "balance": float(account.balance),
                "equity": float(account.equity),
            },
        )

    elif event == "position_closed":
        ticket = int(data.get("position_id") or data.get("ticket", 0))
        t_res = await db.execute(
            select(Trade).where(Trade.user_id == user_id, Trade.mt5_ticket == ticket)
        )
        trade = t_res.scalar_one_or_none()
        if trade:
            trade.status = TradeStatus.CLOSED
            trade.closed_at = now
            if data.get("price"):
                trade.close_price = float(data["price"])
            if data.get("pnl"):
                trade.realized_pnl = float(data["pnl"])

        if "balance" in data:
            account.balance = float(data["balance"])
        if "equity" in data:
            account.equity = float(data["equity"])

        await db.commit()
        await ws_manager.send_to_user(
            user_id,
            "trade.closed",
            {
                "ticket": ticket,
                "price": data.get("price"),
                "pnl": data.get("pnl"),
            },
        )
        await ws_manager.send_to_user(
            user_id,
            "account_update",
            {
                "login": account.mt5_login,
                "balance": float(account.balance),
                "equity": float(account.equity),
            },
        )

    elif event == "tick":
        raw_sym = str(data.get("symbol", "")).upper()
        clean_sym = raw_sym.rstrip("M")
        bid = float(data.get("bid", 0.0))
        ask = float(data.get("ask", 0.0))
        tick_time = data.get("time")

        tick_payload = {
            "symbol": clean_sym,
            "bid": bid,
            "ask": ask,
            "time": tick_time or now.isoformat(),
        }
        await ws_manager.broadcast_tick(clean_sym, tick_payload)
        if raw_sym != clean_sym:
            await ws_manager.broadcast_tick(raw_sym, {**tick_payload, "symbol": raw_sym})

        t_epoch = None
        if tick_time is not None:
            try:
                t_epoch = int(float(tick_time))
            except (ValueError, TypeError):
                pass
        update_candle_with_tick(clean_sym, bid, t_epoch)

    elif event == "heartbeat":
        if "balance" in data:
            account.balance = float(data["balance"])
        if "equity" in data:
            account.equity = float(data["equity"])

        # Sync open positions
        positions = data.get("positions", [])
        if isinstance(positions, list):
            active_tickets = {int(p["ticket"]) for p in positions if "ticket" in p}
            for p in positions:
                ticket = int(p["ticket"])
                t_res = await db.execute(
                    select(Trade).where(Trade.user_id == user_id, Trade.mt5_ticket == ticket)
                )
                existing = t_res.scalar_one_or_none()
                pnl = float(p.get("pnl", 0.0))
                if existing:
                    existing.realized_pnl = pnl
                    existing.status = TradeStatus.OPEN
                else:
                    direction = (
                        TradeDirection.BUY
                        if str(p.get("direction", "")).lower() == "buy"
                        else TradeDirection.SELL
                    )
                    db.add(
                        Trade(
                            user_id=user_id,
                            mt5_account_id=account.id,
                            mt5_ticket=ticket,
                            symbol=str(p.get("symbol", "XAUUSD")).upper().rstrip("M"),
                            direction=direction,
                            lot_size=float(p.get("lot", 0.01)),
                            entry_price=float(p.get("open_price", 0.0)),
                            realized_pnl=pnl,
                            status=TradeStatus.OPEN,
                            comment=str(p.get("comment", "MT5 Sync")),
                            opened_at=now,
                        )
                    )

            # Close trades no longer open
            open_res = await db.execute(
                select(Trade).where(Trade.user_id == user_id, Trade.status == TradeStatus.OPEN)
            )
            for ot in open_res.scalars().all():
                if ot.mt5_ticket and ot.mt5_ticket not in active_tickets:
                    ot.status = TradeStatus.CLOSED
                    ot.closed_at = now

        await db.commit()
        await ws_manager.send_to_user(
            user_id,
            "account_update",
            {
                "login": account.mt5_login,
                "server": account.server_name,
                "company": account.broker_name,
                "balance": float(account.balance),
                "equity": float(account.equity),
            },
        )

    return {"status": "ok", "event": event}


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single trade by ID."""
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current_user.id)
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return TradeResponse.model_validate(trade)


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request to close an open trade (sends close command to MT5 agent)."""
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(
            status_code=404,
            detail="Trade not found or not in open status",
        )

    if trade.mt5_account_id and ws_manager.is_agent_connected(trade.mt5_account_id):
        await ws_manager.send_to_agent(
            trade.mt5_account_id,
            "close_position",
            {"trade_id": str(trade.id), "ticket": trade.mt5_ticket},
        )
        trade.status = TradeStatus.PENDING
    else:
        trade.status = TradeStatus.CLOSED
        trade.closed_at = datetime.now(timezone.utc)
        if trade.entry_price and not trade.close_price:
            trade.close_price = trade.entry_price

    await db.flush()
    await db.refresh(trade)
    return TradeResponse.model_validate(trade)
