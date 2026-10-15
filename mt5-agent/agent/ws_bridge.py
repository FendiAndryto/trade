"""
WebSocket Bridge — connects MT5 Agent to the main TradeGear server.

Handles:
- Persistent WebSocket connection with auto-reconnect
- Receiving trade commands from server
- Streaming price ticks to server
- Sending execution reports back
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import websockets

from agent.config import AgentConfig
from agent.mt5_client import MT5Client


class WebSocketBridge:
    """Maintains a persistent WebSocket connection to the TradeGear server."""

    def __init__(self, server_url: str, agent_token: str, mt5_client: MT5Client):
        self._server_url = server_url
        self._agent_token = agent_token
        self._mt5 = mt5_client
        self._ws = None
        self._running = False
        self._reconnect_delay = 1  # seconds, doubles on failure (max 60)

    async def run(self):
        """Main loop — connect, handle messages, stream ticks, auto-reconnect."""
        self._running = True

        while self._running:
            try:
                async with websockets.connect(
                    f"{self._server_url}?agent_token={self._agent_token}",
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1  # Reset on successful connect
                    print("✅ Connected to TradeGear server")

                    # Send initial account info and candles
                    await self._send_account_update()
                    await self._send_candles("XAUUSD", "1h", 120)

                    # Run message handler and tick streamer concurrently
                    await asyncio.gather(
                        self._handle_messages(),
                        self._stream_ticks(),
                        self._periodic_account_sync(),
                    )

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                print(f"⚠️  Connection lost: {e}")
                self._ws = None

                if self._running:
                    print(f"🔄 Reconnecting in {self._reconnect_delay}s...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def _handle_messages(self):
        """Listen for commands from the server."""
        async for message in self._ws:
            try:
                data = json.loads(message)
                event = data.get("event", "")

                if event == "execute_order":
                    await self._handle_order(data.get("data", {}))
                elif event == "close_position":
                    await self._handle_close(data.get("data", {}))
                elif event == "request_account":
                    await self._send_account_update()
                elif event == "request_candles":
                    sym = data.get("data", {}).get("symbol", "XAUUSD")
                    tf = data.get("data", {}).get("timeframe", "1h")
                    await self._send_candles(sym, tf, 120)
                elif event == "pong":
                    pass  # Keepalive response

            except json.JSONDecodeError:
                print(f"⚠️  Invalid message: {message[:100]}")

    async def _handle_order(self, data: dict):
        """Execute a trade order from the server."""
        result = self._mt5.send_market_order(
            symbol=data.get("symbol", "XAUUSD"),
            direction=data.get("direction", "buy"),
            lot=data.get("lot", 0.01),
            sl=data.get("sl"),
            tp=data.get("tp"),
            comment=data.get("comment", "TradeGear"),
            magic=data.get("magic", 0),
        )

        # Send execution report back
        await self._send({
            "event": "execution_report",
            "data": {
                "trade_id": data.get("trade_id"),
                "success": result.success,
                "ticket": result.ticket,
                "price": result.price,
                "volume": result.volume,
                "comment": result.comment,
                "retcode": result.retcode,
            },
        })

    async def _handle_close(self, data: dict):
        """Close a position."""
        ticket = data.get("ticket")
        if ticket:
            result = self._mt5.close_position(ticket)
            await self._send({
                "event": "close_report",
                "data": {
                    "trade_id": data.get("trade_id"),
                    "ticket": ticket,
                    "success": result.success,
                    "price": result.price,
                    "comment": result.comment,
                },
            })

    async def _stream_ticks(self):
        """Stream price ticks to the server."""
        from agent.config import AgentConfig
        config = AgentConfig.from_env()
        symbols = config.tick_symbols
        interval = config.tick_interval_ms / 1000.0

        while self._running and self._ws:
            for symbol in symbols:
                tick = self._mt5.get_tick(symbol)
                if tick:
                    await self._send({
                        "event": "tick",
                        "data": {
                            "symbol": tick.symbol,
                            "bid": tick.bid,
                            "ask": tick.ask,
                            "time": tick.time,
                        },
                    })
            await asyncio.sleep(interval)

    async def _periodic_account_sync(self):
        """Sync account info every 5 seconds."""
        while self._running and self._ws:
            await self._send_account_update()
            await asyncio.sleep(5)

    async def _send_account_update(self):
        """Send current account info and open positions to server."""
        info = self._mt5.account_info()
        positions = self._mt5.get_open_positions()
        if info:
            await self._send({
                "event": "account_update",
                "data": {
                    "login": info.login,
                    "server": getattr(info, "server", ""),
                    "company": getattr(info, "company", ""),
                    "balance": info.balance,
                    "equity": info.equity,
                    "margin": info.margin,
                    "margin_free": info.margin_free,
                    "margin_level": info.margin_level,
                    "currency": getattr(info, "currency", "USD"),
                    "positions": positions,
                },
            })

    async def _send_candles(self, symbol: str = "XAUUSD", timeframe: str = "1h", count: int = 120):
        """Fetch and stream real candles from MT5."""
        candles = self._mt5.get_candles(symbol, timeframe, count)
        if candles:
            await self._send({
                "event": "candles_update",
                "data": {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": candles,
                },
            })

    async def _send(self, data: dict):
        """Send JSON data to the server."""
        if self._ws:
            try:
                await self._ws.send(json.dumps(data))
            except Exception:
                pass  # Connection likely closed, will reconnect

    async def close(self):
        """Close the connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
