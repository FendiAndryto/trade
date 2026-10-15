"""
Strategy routes — CRUD for trading strategies.
"""

import secrets
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.api_token import ApiToken
from app.models.risk_profile import RiskProfile
from app.models.strategy import Strategy
from app.models.user import User
from app.schemas.strategy import (
    RiskProfileSchema,
    StrategyCreateRequest,
    StrategyResponse,
    StrategyUpdateRequest,
)

router = APIRouter(prefix="/strategies", tags=["Strategies"])
settings = get_settings()


def _build_webhook_url(strategy_id: UUID) -> str:
    return f"/api/v1/webhook/{strategy_id}"


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all strategies for the current user."""
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.risk_profile))
        .where(Strategy.user_id == current_user.id)
        .order_by(Strategy.created_at.desc())
    )
    strategies = result.scalars().all()
    return [
        StrategyResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            is_active=s.is_active,
            webhook_url=_build_webhook_url(s.id),
            risk_profile=(
                RiskProfileSchema.model_validate(s.risk_profile) if s.risk_profile else None
            ),
            created_at=s.created_at,
        )
        for s in strategies
    ]


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: StrategyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new strategy with risk profile and auto-generated API token."""
    # Create strategy
    strategy = Strategy(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
    )
    db.add(strategy)
    await db.flush()

    # Create risk profile
    risk = RiskProfile(
        strategy_id=strategy.id,
        **body.risk_profile.model_dump(),
    )
    db.add(risk)

    # Auto-create API token if user doesn't have one
    result = await db.execute(
        select(ApiToken).where(
            ApiToken.user_id == current_user.id,
            ApiToken.is_active == True,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is None:
        raw_token = secrets.token_urlsafe(32)
        api_token = ApiToken(
            user_id=current_user.id,
            token_hash=sha256(raw_token.encode()).hexdigest(),
            label="Auto-generated",
        )
        db.add(api_token)

    await db.flush()
    await db.refresh(strategy)

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        is_active=strategy.is_active,
        webhook_url=_build_webhook_url(strategy.id),
        risk_profile=body.risk_profile,
        created_at=strategy.created_at,
    )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single strategy by ID."""
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.risk_profile))
        .where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        is_active=strategy.is_active,
        webhook_url=_build_webhook_url(strategy.id),
        risk_profile=(
            RiskProfileSchema.model_validate(strategy.risk_profile)
            if strategy.risk_profile
            else None
        ),
        created_at=strategy.created_at,
    )


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    body: StrategyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategy's name, description, or active status."""
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.risk_profile))
        .where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if body.name is not None:
        strategy.name = body.name
    if body.description is not None:
        strategy.description = body.description
    if body.is_active is not None:
        strategy.is_active = body.is_active

    await db.flush()
    await db.refresh(strategy)

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        is_active=strategy.is_active,
        webhook_url=_build_webhook_url(strategy.id),
        risk_profile=(
            RiskProfileSchema.model_validate(strategy.risk_profile)
            if strategy.risk_profile
            else None
        ),
        created_at=strategy.created_at,
    )


@router.put("/{strategy_id}/risk", response_model=RiskProfileSchema)
async def update_risk_profile(
    strategy_id: UUID,
    body: RiskProfileSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a strategy's risk profile."""
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.risk_profile))
        .where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.risk_profile is None:
        risk = RiskProfile(strategy_id=strategy.id, **body.model_dump())
        db.add(risk)
    else:
        for key, value in body.model_dump().items():
            setattr(strategy.risk_profile, key, value)

    await db.flush()
    return body


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategy and its associated risk profile, logs, and trades."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    )
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    await db.delete(strategy)
