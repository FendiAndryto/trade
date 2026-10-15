"""
Lot Size Calculator — risk-based position sizing.

Supports major forex pairs and metals (XAUUSD, XAGUSD).
"""

# Pip values per 1.0 standard lot for common instruments
# These are approximate and should be fetched from MT5 in production
PIP_VALUES: dict[str, dict] = {
    "XAUUSD": {"pip_size": 0.1, "pip_value": 10.0},  # Gold: 1 pip = $0.10, value per lot = $10
    "XAGUSD": {"pip_size": 0.01, "pip_value": 50.0},  # Silver
    "EURUSD": {"pip_size": 0.0001, "pip_value": 10.0},
    "GBPUSD": {"pip_size": 0.0001, "pip_value": 10.0},
    "USDJPY": {"pip_size": 0.01, "pip_value": 6.67},  # Approximate
    "AUDUSD": {"pip_size": 0.0001, "pip_value": 10.0},
    "USDCHF": {"pip_size": 0.0001, "pip_value": 10.0},
    "USDCAD": {"pip_size": 0.0001, "pip_value": 7.50},  # Approximate
    "NZDUSD": {"pip_size": 0.0001, "pip_value": 10.0},
}


def get_pip_info(symbol: str) -> dict:
    """Get pip size and pip value for a symbol."""
    symbol = symbol.upper()
    if symbol in PIP_VALUES:
        return PIP_VALUES[symbol]
    # Default for unknown pairs (assume standard forex)
    return {"pip_size": 0.0001, "pip_value": 10.0}


def price_to_pips(symbol: str, price_distance: float) -> float:
    """Convert a price distance to pips for the given symbol."""
    info = get_pip_info(symbol)
    return abs(price_distance) / info["pip_size"]


def calculate_lot_size(
    account_balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    symbol: str = "XAUUSD",
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Calculate position size based on risk percentage and stop loss distance.

    Args:
        account_balance: Current account balance in USD.
        risk_percent: Risk per trade as percentage (e.g., 1.0 = 1%).
        stop_loss_pips: Stop loss distance in pips.
        symbol: Trading symbol (determines pip value).
        min_lot: Minimum allowed lot size.
        max_lot: Maximum allowed lot size.

    Returns:
        Calculated lot size, clamped to min/max bounds.

    Examples:
        >>> calculate_lot_size(10000, 1.0, 50, "XAUUSD")
        0.2
        >>> calculate_lot_size(5000, 2.0, 100, "EURUSD")
        0.1
    """
    if stop_loss_pips <= 0:
        return min_lot

    if account_balance <= 0:
        return min_lot

    info = get_pip_info(symbol)
    risk_amount = account_balance * (risk_percent / 100)
    lot_size = risk_amount / (stop_loss_pips * info["pip_value"])

    # Round to 2 decimal places (MT5 standard)
    lot_size = round(lot_size, 2)

    # Clamp to bounds
    lot_size = max(min_lot, min(lot_size, max_lot))

    return lot_size


def calculate_lot_from_prices(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    symbol: str = "XAUUSD",
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Calculate lot size from entry and stop loss prices.

    Convenience wrapper that converts price distance to pips first.
    """
    sl_pips = price_to_pips(symbol, abs(entry_price - stop_loss_price))
    return calculate_lot_size(
        account_balance=account_balance,
        risk_percent=risk_percent,
        stop_loss_pips=sl_pips,
        symbol=symbol,
        min_lot=min_lot,
        max_lot=max_lot,
    )
