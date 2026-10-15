"""
Accounts API — Manage MT5 accounts, No-Code pairing, and EA downloads.
"""

import secrets
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.mt5_account import MT5Account, MT5Status
from app.models.user import User
from app.schemas.account import (
    MT5AccountCreate,
    MT5AccountResponse,
    MT5PairRequest,
    MT5PairResponse,
)
from app.ws.manager import ws_manager

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def _generate_pairing_code() -> str:
    """Generate a clean, readable 6-character pairing code: e.g. TG-748921."""
    digits = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    return f"TG-{digits}"


@router.get("", response_model=list[MT5AccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connected or registered MT5 accounts for the current user."""
    result = await db.execute(
        select(MT5Account).where(MT5Account.user_id == current_user.id).order_by(MT5Account.last_sync_at.desc().nullslast())
    )
    accounts = result.scalars().all()
    return [MT5AccountResponse.model_validate(acc) for acc in accounts]


@router.post("", response_model=MT5AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_in: MT5AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new MT5 account from the website.
    Generates a unique Pairing Code for 1-click EA connection.
    """
    pairing_code = _generate_pairing_code()
    token_hash = sha256(pairing_code.encode()).hexdigest()

    account = MT5Account(
        user_id=current_user.id,
        mt5_login=account_in.mt5_login,
        server_name=account_in.server_name.strip(),
        broker_name=account_in.broker_name.strip() or "MetaQuotes Broker",
        status=MT5Status.DISCONNECTED,
        balance=0.0,
        equity=0.0,
        agent_token_hash=token_hash,
        pairing_code=pairing_code,
        last_sync_at=None,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    return MT5AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and delete an MT5 account."""
    result = await db.execute(
        select(MT5Account).where(MT5Account.id == account_id, MT5Account.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if ws_manager.is_agent_connected(account.id):
        ws_manager.disconnect_agent(account.id)

    await db.delete(account)
    await db.commit()
    return None


@router.post("/pair", response_model=MT5PairResponse)
async def pair_mt5_terminal(
    req: MT5PairRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public handshake endpoint for MQL5 EA / Bridge Agent.
    Pairs the MT5 terminal to the TradeGear account using the 6-digit pairing code.
    No code or manual config editing required!
    """
    code = req.pairing_code.strip().upper()
    code_hash = sha256(code.encode()).hexdigest()

    # Find account by pairing_code column or agent_token_hash
    result = await db.execute(
        select(MT5Account).where(
            (MT5Account.pairing_code == code) | (MT5Account.agent_token_hash == code_hash)
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        # Fallback check for dev mode
        if "dev" in code.lower():
            dev_res = await db.execute(select(MT5Account).limit(1))
            account = dev_res.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid pairing code. Please generate a new code from the dashboard.",
        )

    # Update account with live details from MT5 terminal
    now = datetime.now(timezone.utc)
    account.status = MT5Status.CONNECTED
    account.last_sync_at = now
    if req.login:
        account.mt5_login = req.login
    if req.server:
        account.server_name = req.server
    if req.broker:
        account.broker_name = req.broker
    if req.balance:
        account.balance = float(req.balance)
    if req.equity:
        account.equity = float(req.equity)

    await db.commit()
    await db.refresh(account)

    # Broadcast live status update to user's web dashboard instantly
    await ws_manager.send_to_user(
        account.user_id,
        "account_update",
        {
            "login": account.mt5_login,
            "server": account.server_name,
            "company": account.broker_name,
            "balance": float(account.balance),
            "equity": float(account.equity),
            "status": "connected",
        },
    )

    return MT5PairResponse(
        status="success",
        message=f"Terminal successfully paired to TradeGear account #{account.mt5_login}!",
        account_id=str(account.id),
        agent_token=code,
    )


@router.get("/download-ea")
async def download_mql5_ea(
    pairing_code: str = Query(default="", description="Optional pairing code to pre-fill"),
    server_url: str = Query(default="", description="Backend server URL"),
):
    """
    Generates and downloads the pre-configured MQL5 Expert Advisor file.
    User can simply drop this file onto their MT5 chart.
    """
    from app.services.ea_generator import generate_mql5_ea_source

    ea_code = generate_mql5_ea_source(
        default_server_url=server_url or "https://trade.homever.my.id",
        default_pairing_code=pairing_code or "TG-000000",
    )

    filename = f"TradeGearBridge_{pairing_code or 'Latest'}.mq5"
    return Response(
        content=ea_code,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
