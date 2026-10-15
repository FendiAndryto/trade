"""
Candle service — handles persistent caching, real-time bar rollover, and fallback candle generation.
"""

import random
import time
from typing import Any

# In-memory storage (accessible across API routes and websockets)
_cached_candles: dict[str, list[dict[str, Any]]] = {}


def get_or_generate_candles(
    symbol: str = "XAUUSD", count: int = 120, timeframe_sec: int = 3600
) -> list[dict[str, Any]]:
    """
    Get latest candlestick history for symbol.
    If MT5 has not streamed candles yet, dynamically generates realistic historical OHLC bars
    so the chart never renders blank.
    """
    sym = symbol.upper().rstrip("M")
    if sym in _cached_candles and len(_cached_candles[sym]) > 0:
        return _cached_candles[sym]

    base_prices = {
        "XAUUSD": 4154.0,
        "EURUSD": 1.0850,
        "GBPUSD": 1.2980,
        "BTCUSD": 67400.0,
    }
    current_price = base_prices.get(sym, 4154.0)
    digits = 2 if sym in ("XAUUSD", "BTCUSD") else 5
    volatility = (
        6.5
        if sym == "XAUUSD"
        else 0.0015
        if "USD" in sym and sym != "BTCUSD"
        else 250.0
        if sym == "BTCUSD"
        else 1.0
    )

    now_sec = int(time.time())
    current_bar_time = now_sec - (now_sec % timeframe_sec)
    start_time = current_bar_time - (count * timeframe_sec)

    candles = []
    # Seed deterministic random walk based on current day and symbol
    rng = random.Random(hash(sym + str(now_sec // 86400)) & 0xFFFFFFFF)

    price = current_price - (count * 0.05 * volatility)
    for i in range(count):
        bar_time = start_time + (i * timeframe_sec)
        open_p = round(price, digits)
        change = (rng.random() - 0.49) * volatility
        close_p = round(open_p + change, digits)
        high_p = round(max(open_p, close_p) + rng.random() * volatility * 0.5, digits)
        low_p = round(min(open_p, close_p) - rng.random() * volatility * 0.5, digits)

        candles.append(
            {
                "time": bar_time,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
            }
        )
        price = close_p

    _cached_candles[sym] = candles
    return candles


def update_candle_with_tick(
    symbol: str, price: float, tick_time: int | None = None, timeframe_sec: int = 3600
):
    """Update current active candlestick or roll over to a new bar when timeframe ticks over."""
    sym = symbol.upper().rstrip("M")
    candles = get_or_generate_candles(sym)
    if not candles:
        return

    # If cache was generated with old price reference (discrepancy > 15%), re-seed to avoid vertical spike
    last_candle = candles[-1]
    if abs(last_candle["close"] - price) > (price * 0.15):
        _cached_candles.pop(sym, None)
        candles = get_or_generate_candles(sym)
        last_candle = candles[-1]

    now_sec = tick_time or int(time.time())
    bar_time = now_sec - (now_sec % timeframe_sec)

    if last_candle["time"] == bar_time:
        # Update current bar
        last_candle["close"] = price
        last_candle["high"] = max(last_candle["high"], price)
        last_candle["low"] = min(last_candle["low"], price)
    elif bar_time > last_candle["time"]:
        # New candle bar rollover!
        new_candle = {
            "time": bar_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
        }
        candles.append(new_candle)
        if len(candles) > 300:
            candles.pop(0)


def set_candles(symbol: str, candles: list[dict[str, Any]]):
    """Store actual candles fetched from MT5 terminal."""
    sym = symbol.upper().rstrip("M")
    if candles and isinstance(candles, list):
        _cached_candles[sym] = candles
