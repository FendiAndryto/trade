"""
TradeGear Database Seeder — seeds initial admin user, dev API tokens, MT5 account, and strategy.
Usage: python seed.py
"""

import asyncio
import sys
from hashlib import sha256
from uuid import UUID

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

from app.core.security import hash_password
from app.database import async_session_factory
from app.models.api_token import ApiToken
from app.models.mt5_account import MT5Account, MT5Status
from app.models.risk_profile import RiskProfile
from app.models.strategy import Strategy
from app.models.user import PlanTier, User

DEFAULT_STRATEGY_ID = UUID("6465a5ac-feb3-4247-9ee5-706a1f63daa4")
DEFAULT_USER_EMAIL = "trader@tradegear.io"
DEFAULT_TOKEN_PLAIN = "dev-test-token"
DEFAULT_AGENT_SECRET = "dev-agent-secret"


async def seed():
    print("[*] Seeding TradeGear Database...")
    async with async_session_factory() as db:
        # 1. User
        res = await db.execute(select(User).where(User.email == DEFAULT_USER_EMAIL))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=DEFAULT_USER_EMAIL,
                password_hash=hash_password("password123"),
                display_name="Trader Fendi",
                plan=PlanTier.PRO,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"[✓] Created User: {user.email} ({user.id})")
        else:
            print(f"[i] User already exists: {user.email}")

        # 2. API Token
        token_hash = sha256(DEFAULT_TOKEN_PLAIN.encode()).hexdigest()
        res = await db.execute(select(ApiToken).where(ApiToken.token_hash == token_hash))
        token = res.scalar_one_or_none()
        if not token:
            token = ApiToken(
                user_id=user.id,
                token_hash=token_hash,
                label="Development Simulator Token",
                is_active=True,
            )
            db.add(token)
            await db.flush()
            print(f"[✓] Created API Token: {DEFAULT_TOKEN_PLAIN}")
        else:
            print(f"[i] API Token already exists: {DEFAULT_TOKEN_PLAIN}")

        # 3. MT5 Account
        agent_token_hash = sha256(DEFAULT_AGENT_SECRET.encode()).hexdigest()
        res = await db.execute(
            select(MT5Account).where(MT5Account.agent_token_hash == agent_token_hash)
        )
        mt5_acc = res.scalar_one_or_none()
        if not mt5_acc:
            mt5_acc = MT5Account(
                user_id=user.id,
                mt5_login=0,
                server_name="",
                broker_name="",
                status=MT5Status.DISCONNECTED,
                balance=1000.0,
                equity=1000.0,
                agent_token_hash=agent_token_hash,
            )
            db.add(mt5_acc)
            await db.flush()
            print(f"[✓] Created MT5 Account record ({mt5_acc.id})")
        else:
            print(f"[i] MT5 Account record already exists ({mt5_acc.id})")

        # 4. Strategy
        res = await db.execute(select(Strategy).where(Strategy.id == DEFAULT_STRATEGY_ID))
        strat = res.scalar_one_or_none()
        if not strat:
            strat = Strategy(
                id=DEFAULT_STRATEGY_ID,
                user_id=user.id,
                name="Gold Scalper Pro XAUUSD",
                description="Automated 15m Trend & Pullback strategy for XAUUSD",
                is_active=True,
                webhook_config={
                    "allowed_symbols": ["XAUUSD", "EURUSD"],
                    "require_sl": True,
                    "default_lot": 0.01,
                },
            )
            db.add(strat)
            await db.flush()
            print(f"[✓] Created Strategy: {strat.name} ({strat.id})")
        else:
            print(f"[i] Strategy already exists: {strat.name}")

        # 5. Risk Profile
        res = await db.execute(
            select(RiskProfile).where(RiskProfile.strategy_id == DEFAULT_STRATEGY_ID)
        )
        risk = res.scalar_one_or_none()
        if not risk:
            risk = RiskProfile(
                strategy_id=DEFAULT_STRATEGY_ID,
                risk_per_trade_pct=1.0,
                daily_loss_limit_pct=3.0,
                max_concurrent_trades=3,
                max_lot_size=5.0,
                min_lot_size=0.01,
                session_filter={"london": True, "new_york": True, "asian": False},
                advanced_rules={"require_sl": True, "max_spread_points": 35},
            )
            db.add(risk)
            await db.flush()
            print("[✓] Created Risk Profile (1% risk, 3% daily limit, max 3 trades)")
        else:
            print("[i] Risk Profile already exists")

        await db.commit()
    print("[✓] Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
