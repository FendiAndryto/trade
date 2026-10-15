"""
Auth routes — register, login, refresh, logout, profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account and initialize default workspace assets."""
    import secrets
    from hashlib import sha256
    from app.models.api_token import ApiToken
    from app.models.mt5_account import MT5Account, MT5Status
    from app.models.risk_profile import RiskProfile
    from app.models.strategy import Strategy

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.flush()

    # Initialize default MT5 account bridge
    agent_token_hash = sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    mt5 = MT5Account(
        user_id=user.id,
        mt5_login=0,
        server_name="",
        broker_name="",
        status=MT5Status.DISCONNECTED,
        balance=0.0,
        equity=0.0,
        agent_token_hash=agent_token_hash,
    )
    db.add(mt5)

    # Initialize default starter strategy
    strategy = Strategy(
        user_id=user.id,
        name="Gold Scalper Pro XAUUSD",
        description="Automated starter strategy for TradingView webhooks",
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

    # Initialize default Webhook API Token
    raw_tok = secrets.token_urlsafe(32)
    api_token = ApiToken(
        user_id=user.id,
        token_hash=sha256(raw_tok.encode()).hexdigest(),
        label="Default Webhook Token",
        is_active=True,
    )
    db.add(api_token)

    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password, returns JWT token pair."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    from uuid import UUID

    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    if body.display_name is not None:
        current_user.display_name = body.display_name
    await db.flush()
    await db.refresh(current_user)
    return current_user
