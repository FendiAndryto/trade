"""
Unit tests for lot size calculator.
"""

from app.services.lot_calculator import (
    calculate_lot_from_prices,
    calculate_lot_size,
    price_to_pips,
)


def test_price_to_pips_gold():
    # Gold 1 pip = 0.1
    pips = price_to_pips("XAUUSD", 5.0)
    assert pips == 50.0


def test_price_to_pips_forex():
    # EURUSD 1 pip = 0.0001
    pips = price_to_pips("EURUSD", 0.0020)
    assert round(pips, 2) == 20.0


def test_calculate_lot_size_basic():
    # 10,000 balance, 1% risk ($100), 50 pips SL on XAUUSD ($10/pip/lot)
    # Calculation: 100 / (50 * 10) = 0.20 lots
    lot = calculate_lot_size(
        account_balance=10000.0,
        risk_percent=1.0,
        stop_loss_pips=50.0,
        symbol="XAUUSD",
    )
    assert lot == 0.20


def test_calculate_lot_size_clamping():
    # Should clamp to max_lot
    lot = calculate_lot_size(
        account_balance=100000.0,
        risk_percent=5.0,
        stop_loss_pips=5.0,
        symbol="XAUUSD",
        max_lot=1.0,
    )
    assert lot == 1.0

    # Should clamp to min_lot
    lot_small = calculate_lot_size(
        account_balance=100.0,
        risk_percent=0.1,
        stop_loss_pips=500.0,
        symbol="XAUUSD",
        min_lot=0.01,
    )
    assert lot_small == 0.01


def test_calculate_lot_from_prices():
    # Entry: 2650.0, SL: 2645.0 -> 5.0 distance = 50 pips on XAUUSD
    lot = calculate_lot_from_prices(
        account_balance=10000.0,
        risk_percent=1.0,
        entry_price=2650.0,
        stop_loss_price=2645.0,
        symbol="XAUUSD",
    )
    assert lot == 0.20
