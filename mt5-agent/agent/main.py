"""
MT5 Agent — Bridge between main server and MetaTrader 5 terminal.

Runs on Windows machine with MT5 terminal installed.
Connects to main server via WebSocket for receiving trade commands
and streaming price data back.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent.config import AgentConfig
from agent.mt5_client import MT5Client
from agent.ws_bridge import WebSocketBridge


async def main():
    """Main entry point for the MT5 Agent."""
    config = AgentConfig.from_env()

    print(f"🤖 MT5 Agent starting...")
    print(f"   Server: {config.server_url}")
    print(f"   MT5 Login: {config.mt5_login}")
    print(f"   MT5 Server: {config.mt5_server}")

    # Initialize MT5 connection
    mt5 = MT5Client(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        path=config.mt5_path,
    )

    if not mt5.connect():
        print("❌ Failed to connect to MT5 terminal")
        sys.exit(1)

    print(f"✅ Connected to MT5 — Account: {mt5.account_info()}")

    # Connect to main server via WebSocket
    bridge = WebSocketBridge(
        server_url=config.server_url,
        agent_token=config.agent_token,
        mt5_client=mt5,
    )

    try:
        await bridge.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await shutdown(bridge, mt5)


async def shutdown(bridge: WebSocketBridge, mt5: MT5Client):
    """Graceful shutdown."""
    print("\n👋 Shutting down MT5 Agent...")
    await bridge.close()
    mt5.disconnect()
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
