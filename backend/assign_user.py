import asyncio
import sys
from sqlalchemy import select, update

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.database import async_session_factory
from app.models.api_token import ApiToken
from app.models.daily_stats import DailyStats
from app.models.mt5_account import MT5Account
from app.models.strategy import Strategy
from app.models.trade import Trade
from app.models.user import User


async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.email == "fendiandryto@gmail.com"))
        user = res.scalar_one_or_none()
        if not user:
            print("User Fendian not found!")
            return

        print(f"Linking seed assets to user {user.email} ({user.id})...")
        await db.execute(update(MT5Account).values(user_id=user.id))
        await db.execute(update(Strategy).values(user_id=user.id))
        await db.execute(update(ApiToken).values(user_id=user.id))
        await db.execute(update(DailyStats).values(user_id=user.id))
        await db.execute(update(Trade).values(user_id=user.id))
        await db.commit()
        print("[✓] Successfully linked MT5 account, strategy, and tokens to Fendian!")


if __name__ == "__main__":
    asyncio.run(main())
