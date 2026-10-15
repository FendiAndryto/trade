"""
MT5 Client — wrapper around the MetaTrader5 Python library.

NOTE: This module requires Windows and the MetaTrader5 pip package.
Install: pip install MetaTrader5
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TickData:
    symbol: str
    bid: float
    ask: float
    time: float


@dataclass
class OrderResult:
    success: bool
    ticket: int | None = None
    price: float | None = None
    volume: float | None = None
    comment: str = ""
    retcode: int = 0


@dataclass
class AccountInfo:
    login: int
    balance: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    currency: str
    server: str
    company: str = ""


class MT5Client:
    """
    Wrapper around the MetaTrader5 Python library.

    Provides a clean interface for:
    - Connecting/disconnecting
    - Sending market orders (BUY/SELL)
    - Closing positions
    - Getting account info
    - Streaming price ticks
    """

    def __init__(self, login: int, password: str, server: str, path: str = ""):
        self._login = login
        self._password = password
        self._server = server
        self._path = path
        self._connected = False

    def connect(self) -> bool:
        """Initialize and connect to MT5 terminal."""
        try:
            import MetaTrader5 as mt5

            init_kwargs = {}
            if self._path:
                init_kwargs["path"] = self._path

            if not mt5.initialize(**init_kwargs):
                print(f"MT5 init failed: {mt5.last_error()}")
                return False

            # If login credentials provided, perform login; otherwise use active account
            if self._login and self._password and self._server:
                if not mt5.login(self._login, password=self._password, server=self._server):
                    print(f"MT5 login failed: {mt5.last_error()}")
                    mt5.shutdown()
                    return False
            else:
                info = mt5.account_info()
                if info is None:
                    print("⚠️ MT5 terminal is open but no active account is logged in.")
                    print("   Please log into your broker account in the MT5 desktop app.")
                    mt5.shutdown()
                    return False

            self._connected = True
            return True

        except ImportError:
            print("❌ MetaTrader5 package not installed. Run: pip install MetaTrader5")
            print("   Note: Only works on Windows with MT5 terminal installed.")
            return False

    def disconnect(self):
        """Shutdown MT5 connection."""
        if self._connected:
            try:
                import MetaTrader5 as mt5
                mt5.shutdown()
            except ImportError:
                pass
            self._connected = False

    def account_info(self) -> AccountInfo | None:
        """Get current account information."""
        try:
            import MetaTrader5 as mt5
            info = mt5.account_info()
            if info is None:
                return None
            return AccountInfo(
                login=info.login,
                balance=info.balance,
                equity=info.equity,
                margin=info.margin,
                margin_free=info.margin_free,
                margin_level=info.margin_level if info.margin_level else 0.0,
                currency=info.currency,
                server=info.server,
                company=getattr(info, "company", ""),
            )
        except ImportError:
            return None

    def _resolve_symbol(self, symbol: str) -> str:
        """Resolve generic symbol (e.g. XAUUSD) to broker-specific symbol (e.g. XAUUSDm)."""
        if not hasattr(self, "_symbol_cache"):
            self._symbol_cache: dict[str, str] = {}

        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]

        try:
            import MetaTrader5 as mt5
            info = mt5.symbol_info(symbol)
            if info:
                if not info.visible:
                    mt5.symbol_select(symbol, True)
                self._symbol_cache[symbol] = symbol
                return symbol

            symbols = mt5.symbols_get()
            if symbols:
                target = symbol.upper()
                for s in symbols:
                    name = s.name.upper()
                    clean = name.rstrip("M").rstrip(".PRO").rstrip(".C").rstrip("_I").rstrip(".RAW").rstrip(".ECN").rstrip("#")
                    if clean == target or name.startswith(target):
                        if not s.visible:
                            mt5.symbol_select(s.name, True)
                        self._symbol_cache[symbol] = s.name
                        return s.name
        except Exception:
            pass

        return symbol

    def send_market_order(
        self,
        symbol: str,
        direction: str,  # "buy" or "sell"
        lot: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
        magic: int = 0,
    ) -> OrderResult:
        """Send a market order."""
        try:
            import MetaTrader5 as mt5

            symbol = self._resolve_symbol(symbol)

            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return OrderResult(success=False, comment=f"Symbol {symbol} not found")

            order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
            price = tick.ask if direction == "buy" else tick.bid

            sym_info = mt5.symbol_info(symbol)
            filling_type = mt5.ORDER_FILLING_IOC
            if sym_info and sym_info.filling_mode == 1:
                filling_type = mt5.ORDER_FILLING_FOK

            clean_comment = (comment or "TradeGear")[:26]

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "deviation": 20,  # Max slippage in points
                "magic": magic,
                "comment": clean_comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type,
            }

            if sl is not None and sl > 0 and sym_info:
                request["sl"] = round(sl, sym_info.digits)
            if tp is not None and tp > 0 and sym_info:
                request["tp"] = round(tp, sym_info.digits)

            result = mt5.order_send(request)
            if result is None:
                return OrderResult(success=False, comment=f"Order send failed: {mt5.last_error()}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    retcode=result.retcode,
                    comment=f"Order rejected: {result.comment}",
                )

            return OrderResult(
                success=True,
                ticket=result.order,
                price=result.price,
                volume=result.volume,
                comment=result.comment,
                retcode=result.retcode,
            )

        except ImportError:
            return OrderResult(success=False, comment="MetaTrader5 package not available")

    def close_position(self, ticket: int) -> OrderResult:
        """Close an open position by ticket number."""
        try:
            import MetaTrader5 as mt5

            position = mt5.positions_get(ticket=ticket)
            if not position:
                return OrderResult(success=False, comment=f"Position {ticket} not found")

            pos = position[0]
            close_type = (
                mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            )
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

            sym_info = mt5.symbol_info(pos.symbol)
            filling_type = mt5.ORDER_FILLING_IOC
            if sym_info and sym_info.filling_mode == 1:
                filling_type = mt5.ORDER_FILLING_FOK

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": "TradeGear close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_type,
            }

            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    retcode=result.retcode if result else 0,
                    comment=f"Close failed: {result.comment if result else 'Unknown error'}",
                )

            return OrderResult(
                success=True,
                ticket=result.order,
                price=result.price,
                volume=result.volume,
            )

        except ImportError:
            return OrderResult(success=False, comment="MetaTrader5 package not available")

    def get_tick(self, symbol: str) -> TickData | None:
        """Get the latest tick for a symbol."""
        try:
            import MetaTrader5 as mt5

            symbol = self._resolve_symbol(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return TickData(
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                time=tick.time,
            )
        except ImportError:
            return None

    def get_open_positions(self) -> list[dict]:
        """Fetch all currently open positions from MT5."""
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get()
            if not positions:
                return []
            res = []
            for p in positions:
                res.append(
                    {
                        "ticket": int(p.ticket),
                        "symbol": str(p.symbol),
                        "direction": "buy" if p.type == 0 else "sell",
                        "lot": float(p.volume),
                        "open_price": float(p.price_open),
                        "current_price": float(p.price_current),
                        "sl_price": float(p.sl) if p.sl > 0 else None,
                        "tp_price": float(p.tp) if p.tp > 0 else None,
                        "pnl": float(p.profit),
                        "comment": str(p.comment),
                        "opened_at": datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
                    }
                )
            return res
        except Exception:
            return []

    def get_candles(
        self, symbol: str = "XAUUSD", timeframe: str = "1h", count: int = 120
    ) -> list[dict]:
        """Fetch historical candlestick data from MT5."""
        try:
            import MetaTrader5 as mt5

            tf_map = {
                "1m": mt5.TIMEFRAME_M1,
                "5m": mt5.TIMEFRAME_M5,
                "15m": mt5.TIMEFRAME_M15,
                "1h": mt5.TIMEFRAME_H1,
                "4h": mt5.TIMEFRAME_H4,
                "1d": mt5.TIMEFRAME_D1,
            }
            tf = tf_map.get(timeframe.lower(), mt5.TIMEFRAME_H1)
            resolved = self._resolve_symbol(symbol)
            rates = mt5.copy_rates_from_pos(resolved, tf, 0, count)
            if rates is None or len(rates) == 0:
                return []
            candles = []
            for r in rates:
                candles.append(
                    {
                        "time": int(r["time"]),
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                    }
                )
            return candles
        except Exception:
            return []

    @property
    def is_connected(self) -> bool:
        return self._connected
