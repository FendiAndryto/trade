"""
Economic News Filter — Protects automated trading against extreme volatility and slippage
during Red Folder / High-Impact events (CPI, Non-Farm Payrolls, FOMC).
"""

from datetime import datetime, timezone
from typing import List, Tuple

# Major recurring high impact keywords
HIGH_IMPACT_KEYWORDS = [
    "CPI",
    "Non-Farm",
    "NFP",
    "FOMC",
    "Fed Interest Rate",
    "ECB Rate",
    "Unemployment Rate",
    "GDP",
]


def is_high_impact_news_window(
    current_time: datetime | None = None,
    buffer_minutes_before: int = 15,
    buffer_minutes_after: int = 15,
    events_schedule: List[dict] | None = None,
) -> Tuple[bool, str]:
    """
    Checks if the current moment falls within a high-impact news blackout window.
    Returns (is_blackout, news_event_title).
    """
    now = current_time or datetime.now(timezone.utc)
    if not events_schedule:
        return False, ""

    for event in events_schedule:
        event_time_str = event.get("time")
        impact = str(event.get("impact", "")).lower()

        if impact not in ("high", "red"):
            continue

        try:
            event_dt = datetime.fromisoformat(event_time_str)
            diff_sec = (now - event_dt).total_seconds()
            diff_min = diff_sec / 60.0

            # Within window: -15 min before to +15 min after
            if -buffer_minutes_before <= diff_min <= buffer_minutes_after:
                return True, event.get("title", "High-Impact Economic News")
        except Exception:
            continue

    return False, ""
