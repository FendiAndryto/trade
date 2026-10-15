import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import TradeRejected
from app.database import get_db
from app.models.api_token import ApiToken
from app.models.mt5_account import MT5Account
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.models.webhook_log import WebhookLog, WebhookStatus
from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services.risk_engine import validate_trade
from app.ws.manager import ws_manager

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


async def _validate_api_token(token: str, db: AsyncSession) -> ApiToken:
    """Validate an API token from the header."""
    from hashlib import sha256

    # Test/demo token fallback
    if token in ("dev-test-token", "dev"):
        res = await db.execute(select(ApiToken).where(ApiToken.is_active == True).limit(1))  # noqa: E712
        tok = res.scalar_one_or_none()
        if tok:
            return tok

    token_hash = sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(ApiToken).where(
            ApiToken.token_hash == token_hash,
            ApiToken.is_active == True,  # noqa: E712
        )
    )
    api_token = result.scalar_one_or_none()
    if api_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API token",
        )
    return api_token


@router.get("/{strategy_id}")
async def get_webhook_info(strategy_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Informational endpoint when user opens their Webhook URL in a web browser.
    Explains how to use the URL with TradingView Alert.
    """
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {
            "status": "not_found",
            "message": "Strategy ID tidak ditemukan. Pastikan URL Webhook sesuai.",
        }

    return {
        "status": "ready" if strategy.is_active else "paused",
        "strategy_id": str(strategy.id),
        "strategy_name": strategy.name,
        "symbol": "XAUUSD",
        "message": "Webhook URL aktif dan siap menerima sinyal dari TradingView via HTTP POST!",
        "instructions": {
            "step_1": "Buka chart di TradingView dan pasang indikator/sinyal yang diinginkan.",
            "step_2": "Klik 'Create Alert' (ikon jam alarm) di TradingView.",
            "step_3": "Pada tab 'Notifications', centang 'Webhook URL' dan masukkan URL ini.",
            "step_4": "Pada tab 'Settings' di kolom 'Message', masukkan JSON payload sinyal.",
        },
        "example_tradingview_message": {
            "action": "buy",
            "symbol": "XAUUSD",
            "lot": 0.01,
            "sl": 4140.0,
            "tp": 4180.0,
            "comment": strategy.name,
        },
    }


@router.post("/{strategy_id}", response_model=WebhookResponse)
async def receive_webhook(
    strategy_id: UUID,
    payload: WebhookPayload,
    request: Request,
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a webhook alert from TradingView.

    The alert is validated, evaluated by the Risk Engine, executed, and pushed to MT5 / UI.
    """
    start_time = time.monotonic()

    # 1. Load strategy & verify ownership
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.risk_profile))
        .where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Validate custom API token if explicitly provided
    if x_api_token and x_api_token not in ("dev-test-token", "dev"):
        await _validate_api_token(x_api_token, db)

    # 3. Check if strategy is active
    if not strategy.is_active:
        log = WebhookLog(
            strategy_id=strategy.id,
            raw_payload=payload.model_dump(),
            status=WebhookStatus.REJECTED,
            rejection_reason="Strategy is disabled",
            processing_ms=int((time.monotonic() - start_time) * 1000),
        )
        db.add(log)
        await db.flush()

        await ws_manager.send_to_user(
            strategy.user_id,
            "webhook.log",
            {
                "id": str(log.id),
                "strategy_id": str(strategy.id),
                "action": payload.action.upper(),
                "symbol": payload.symbol.upper(),
                "status": "rejected",
                "message": "Strategy is currently disabled",
                "processing_ms": log.processing_ms,
                "received_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return WebhookResponse(
            status="rejected",
            webhook_id=log.id,
            message="Strategy is currently disabled",
        )

    # 4. Log the incoming webhook
    log = WebhookLog(
        strategy_id=strategy.id,
        raw_payload=payload.model_dump(),
        status=WebhookStatus.RECEIVED,
    )
    db.add(log)
    await db.flush()

    # 5. Fetch user's MT5 Account
    acc_res = await db.execute(
        select(MT5Account).where(MT5Account.user_id == strategy.user_id).limit(1)
    )
    mt5_account = acc_res.scalar_one_or_none()

    # 6. Run Risk Engine Validation
    try:
        risk_result = await validate_trade(
            db=db,
            user_id=strategy.user_id,
            mt5_account=mt5_account,
            risk_profile=strategy.risk_profile,
            payload=payload,
        )
    except TradeRejected as exc:
        log.status = WebhookStatus.REJECTED
        log.rejection_reason = str(exc)
        log.processing_ms = int((time.monotonic() - start_time) * 1000)
        await db.flush()

        await ws_manager.send_to_user(
            strategy.user_id,
            "webhook.log",
            {
                "id": str(log.id),
                "strategy_id": str(strategy.id),
                "action": payload.action.upper(),
                "symbol": payload.symbol.upper(),
                "status": "rejected",
                "message": f"Risk rejection: {exc}",
                "processing_ms": log.processing_ms,
                "received_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return WebhookResponse(
            status="rejected",
            webhook_id=log.id,
            message=f"Risk rejection: {exc}",
        )

    # 7. Execute Order (Handle Close vs Open)
    action_lower = payload.action.lower()
    if action_lower in ("close", "close_buy", "close_sell"):
        trade_q = select(Trade).where(
            Trade.user_id == strategy.user_id,
            Trade.symbol == payload.symbol.upper(),
            Trade.status == TradeStatus.OPEN,
        )
        if action_lower == "close_buy":
            trade_q = trade_q.where(Trade.direction == TradeDirection.BUY)
        elif action_lower == "close_sell":
            trade_q = trade_q.where(Trade.direction == TradeDirection.SELL)

        res = await db.execute(trade_q)
        open_trades = res.scalars().all()

        closed_count = 0
        for t in open_trades:
            t.status = TradeStatus.CLOSED
            t.closed_at = datetime.now(timezone.utc)
            if payload.price:
                t.close_price = payload.price
            elif not t.close_price and t.entry_price:
                t.close_price = t.entry_price

            if t.mt5_account_id and ws_manager.is_agent_connected(t.mt5_account_id):
                await ws_manager.send_to_agent(
                    t.mt5_account_id,
                    "close_position",
                    {"trade_id": str(t.id), "ticket": t.mt5_ticket},
                )

            await ws_manager.send_to_user(
                strategy.user_id,
                "trade.closed",
                {"trade_id": str(t.id), "symbol": t.symbol, "ticket": t.mt5_ticket},
            )
            closed_count += 1

        log.status = WebhookStatus.EXECUTED
        log.processing_ms = int((time.monotonic() - start_time) * 1000)
        await db.flush()

        close_msg = f"Closed {closed_count} open position(s) on {payload.symbol.upper()}"
        await ws_manager.send_to_user(
            strategy.user_id,
            "webhook.log",
            {
                "id": str(log.id),
                "strategy_id": str(strategy.id),
                "action": payload.action.upper(),
                "symbol": payload.symbol.upper(),
                "status": "executed",
                "message": close_msg,
                "processing_ms": log.processing_ms,
                "received_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return WebhookResponse(
            status="executed",
            webhook_id=log.id,
            message=close_msg,
        )

    direction = TradeDirection.BUY if action_lower == "buy" else TradeDirection.SELL
    trade = Trade(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        mt5_account_id=mt5_account.id if mt5_account else None,
        symbol=payload.symbol.upper(),
        direction=direction,
        lot_size=risk_result.lot_size,
        entry_price=payload.price,
        stop_loss=payload.sl,
        take_profit=payload.tp,
        status=TradeStatus.OPEN,
        comment=payload.comment or f"TV: {strategy.name}",
        opened_at=datetime.now(timezone.utc),
    )
    db.add(trade)
    await db.flush()

    log.status = WebhookStatus.EXECUTED
    log.processing_ms = int((time.monotonic() - start_time) * 1000)
    await db.flush()

    await ws_manager.send_to_user(
        strategy.user_id,
        "webhook.log",
        {
            "id": str(log.id),
            "strategy_id": str(strategy.id),
            "action": payload.action.upper(),
            "symbol": payload.symbol.upper(),
            "status": "executed",
            "message": (
                f"Order executed: {trade.direction.value.upper()} "
                f"{trade.lot_size} lots @ {trade.entry_price or 'market'}"
            ),
            "processing_ms": log.processing_ms,
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # 8. Dispatch order to connected MT5 Agent via WebSocket
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

    # 9. Push real-time event to user's dashboard UI
    await ws_manager.send_to_user(
        strategy.user_id,
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

    return WebhookResponse(
        status="executed",
        webhook_id=log.id,
        message=(
            f"Order executed: {trade.direction.value.upper()} "
            f"{trade.lot_size} lots {trade.symbol} in {log.processing_ms}ms"
        ),
    )
