"""
Exit Manager — Profit Protection Engine.
Handles Auto Break-Even (BEP), Dynamic Trailing Stop, Partial TP, and Daily Profit Target limits.
"""

from typing import Tuple


def get_pip_size(symbol: str) -> float:
    """Returns pip size for given symbol (e.g. 0.01 for JPY & Gold, 0.0001 for Forex)."""
    sym = symbol.upper()
    if "XAU" in sym or "GOLD" in sym:
        return 0.10  # 1 pip in Gold = 10 cents ($0.10)
    elif "JPY" in sym:
        return 0.01
    elif "BTC" in sym:
        return 1.0
    return 0.0001


def evaluate_auto_bep(
    symbol: str,
    direction: str,
    entry_price: float,
    current_price: float,
    current_sl: float | None,
    bep_trigger_pips: float = 25.0,
    buffer_pips: float = 2.0,
) -> Tuple[bool, float]:
    """
    Evaluates if an open position qualifies for Auto Break-Even (BEP).
    If price has moved in profit by >= bep_trigger_pips, adjusts SL to Entry + buffer.
    Returns (should_update, new_sl).
    """
    pip = get_pip_size(symbol)
    trigger_dist = bep_trigger_pips * pip
    buffer_dist = buffer_pips * pip
    is_buy = direction.lower() == "buy"

    if is_buy:
        profit_dist = current_price - entry_price
        if profit_dist >= trigger_dist:
            target_sl = round(entry_price + buffer_dist, 5 if "EUR" in symbol else 2)
            # Only update if current SL is below the new break-even target
            if current_sl is None or current_sl < target_sl:
                return True, target_sl
    else:
        profit_dist = entry_price - current_price
        if profit_dist >= trigger_dist:
            target_sl = round(entry_price - buffer_dist, 5 if "EUR" in symbol else 2)
            # Only update if current SL is above the new break-even target
            if current_sl is None or current_sl > target_sl:
                return True, target_sl

    return False, current_sl or 0.0


def evaluate_trailing_stop(
    symbol: str,
    direction: str,
    entry_price: float,
    current_price: float,
    current_sl: float | None,
    trail_distance_pips: float = 30.0,
    step_pips: float = 10.0,
) -> Tuple[bool, float]:
    """
    Dynamically moves Stop Loss behind trending price to lock in progressive profit.
    Returns (should_update, new_sl).
    """
    pip = get_pip_size(symbol)
    trail_dist = trail_distance_pips * pip
    step_dist = step_pips * pip
    is_buy = direction.lower() == "buy"

    if is_buy:
        ideal_sl = round(current_price - trail_dist, 5 if "EUR" in symbol else 2)
        # Only trail if in profit territory
        if ideal_sl > entry_price:
            if current_sl is None or (ideal_sl - current_sl >= step_dist):
                return True, ideal_sl
    else:
        ideal_sl = round(current_price + trail_dist, 5 if "EUR" in symbol else 2)
        if ideal_sl < entry_price:
            if current_sl is None or (current_sl - ideal_sl >= step_dist):
                return True, ideal_sl

    return False, current_sl or 0.0


def check_daily_profit_target(
    pnl_today: float,
    starting_balance: float,
    target_pct: float,
) -> Tuple[bool, float]:
    """
    Checks if today's profit target has been achieved.
    Returns (is_target_hit, achieved_pct).
    """
    if starting_balance <= 0:
        return False, 0.0

    current_gain_pct = (pnl_today / starting_balance) * 100.0
    is_hit = current_gain_pct >= target_pct
    return is_hit, current_gain_pct
