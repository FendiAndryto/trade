"""
Strategy Engine — Built-in autonomous trading indicators & strategies.
Allows the robot to run without needing an external TradingView paid subscription.
"""

from typing import List, Literal, Optional


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculates Exponential Moving Average (EMA)."""
    if len(prices) < period:
        return []
    multiplier = 2.0 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculates Relative Strength Index (RSI)."""
    if len(prices) <= period:
        return []

    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values = []
    rs = (avg_gain / avg_loss) if avg_loss != 0 else 100.0
    rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = (avg_gain / avg_loss) if avg_loss != 0 else 100.0
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_values


def evaluate_built_in_strategy(
    strategy_type: str, candles: List[dict]
) -> Optional[Literal["buy", "sell"]]:
    """
    Evaluates historical candles against selected built-in algorithmic strategy.
    Returns "buy", "sell", or None.
    """
    if len(candles) < 30:
        return None

    closes = [float(c["close"]) for c in candles]

    if strategy_type == "ema_cross":
        # Fast EMA 9 vs Slow EMA 21 crossover
        fast_ema = calculate_ema(closes, 9)
        slow_ema = calculate_ema(closes, 21)
        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return None

        # Compare last two closed bars
        prev_diff = fast_ema[-2] - slow_ema[-2]
        curr_diff = fast_ema[-1] - slow_ema[-1]

        if prev_diff <= 0 and curr_diff > 0:
            return "buy"  # Bullish golden cross
        elif prev_diff >= 0 and curr_diff < 0:
            return "sell"  # Bearish death cross

    elif strategy_type == "rsi_pullback":
        # RSI 14 mean-reversion
        rsi = calculate_rsi(closes, 14)
        if len(rsi) < 2:
            return None

        prev_rsi = rsi[-2]
        curr_rsi = rsi[-1]

        # Oversold hook up
        if prev_rsi < 30.0 and curr_rsi >= 30.0:
            return "buy"
        # Overbought hook down
        elif prev_rsi > 70.0 and curr_rsi <= 70.0:
            return "sell"

    return None
