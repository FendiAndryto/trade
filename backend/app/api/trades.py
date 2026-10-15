"""
Trades routes — list and manage trades.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.trade import Trade, TradeStatus
from app.models.user import User
from app.schemas.trade import TradeListResponse, TradeResponse
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

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(Trade.opened_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    trades = result.scalars().all()

    return TradeListResponse(
        trades=[TradeResponse.model_validate(t) for t in trades],
        total=total,
        page=page,
        per_page=per_page,
    )


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

    # Send close command to MT5 agent via WebSocket if connected
    if trade.mt5_account_id and ws_manager.is_agent_connected(trade.mt5_account_id):
        await ws_manager.send_to_agent(
            trade.mt5_account_id,
            "close_position",
            {"trade_id": str(trade.id), "ticket": trade.mt5_ticket},
        )
        trade.status = TradeStatus.PENDING
    else:
        # Fallback when MT5 agent is not connected (e.g. simulation/demo)
        trade.status = TradeStatus.CLOSED
        trade.closed_at = datetime.now(timezone.utc)
        if trade.entry_price and not trade.close_price:
            trade.close_price = trade.entry_price

    await db.flush()
    await db.refresh(trade)

    return TradeResponse.model_validate(trade)


@router.get("/candles")
async def get_candles(symbol: str = "XAUUSD"):
    """Get latest candlestick data for symbol."""
    from app.api.websocket import latest_candles
    sym = symbol.upper().rstrip("M")
    candles = latest_candles.get(sym, [])
    return {"symbol": sym, "candles": candles}
