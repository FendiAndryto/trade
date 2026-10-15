"""
Telegram Notification Bot Service.
Sends instant trade executions, TP/SL alerts, and emergency kill-switch controls to mobile.
"""

import os
from typing import Optional


async def send_telegram_alert(message: str) -> bool:
    """
    Sends notification message to configured Telegram chat.
    Safe-fails gracefully if token is not yet configured.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        return False

    try:
        import httpx

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(url, json=payload)
            return res.is_success
    except Exception:
        return False


def format_trade_alert(
    event_type: str,
    symbol: str,
    direction: str,
    lot: float,
    price: float,
    pnl: Optional[float] = None,
    ticket: Optional[int] = None,
) -> str:
    """Formats a clean, readable Telegram alert."""
    icon = "🟢" if direction.lower() == "buy" else "🔴"
    msg = f"<b>TradeGear Robot Alert</b> ⚡\\n\\n"
    msg += f"<b>Event:</b> {event_type.upper()}\\n"
    msg += f"<b>Asset:</b> {icon} {symbol} ({direction.upper()})\\n"
    msg += f"<b>Volume:</b> {lot} lots\\n"
    msg += f"<b>Price:</b> {price}\\n"

    if ticket:
        msg += f"<b>Ticket:</b> #{ticket}\\n"
    if pnl is not None:
        pnl_icon = "💰" if pnl >= 0 else "🔻"
        msg += f"<b>Profit/Loss:</b> {pnl_icon} ${pnl:+.2f}\\n"

    return msg
