import asyncio
import sys
from sqlalchemy import delete

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.database import async_session_factory
from app.models.daily_stats import DailyStats
from app.models.trade import Trade
from app.models.user import User
from app.models.webhook_log import WebhookLog


async def clean():
    print("[*] Cleaning up seeder & dummy data...")
    async with async_session_factory() as db:
        # 1. Delete dummy trades
        res_t = await db.execute(delete(Trade))
        print(f"[✓] Deleted {res_t.rowcount} dummy trades")

        # 2. Delete dummy webhook logs
        res_w = await db.execute(delete(WebhookLog))
        print(f"[✓] Deleted {res_w.rowcount} dummy webhook logs")

        # 3. Delete dummy daily stats
        res_s = await db.execute(delete(DailyStats))
        print(f"[✓] Deleted {res_s.rowcount} dummy daily stats")

        # 4. Delete default seeder user trader@tradegear.io
        res_u = await db.execute(delete(User).where(User.email == "trader@tradegear.io"))
        print(f"[✓] Deleted {res_u.rowcount} seeder user (trader@tradegear.io)")

        await db.commit()
    print("[✓] Database is now clean! Only real account Fendian remains.")


if __name__ == "__main__":
    asyncio.run(clean())
