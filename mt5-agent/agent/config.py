"""
MT5 Agent Configuration.
"""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the MT5 Agent."""

    # Main server connection
    server_url: str
    agent_token: str

    # MT5 credentials
    mt5_login: int
    mt5_password: str
    mt5_server: str
    mt5_path: str  # Path to MT5 terminal (e.g., C:\\Program Files\\MT5\\terminal64.exe)

    # Streaming settings
    tick_symbols: list[str]
    tick_interval_ms: int = 100  # Min interval between tick pushes

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables and .env file."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        symbols = os.getenv("MT5_TICK_SYMBOLS", "XAUUSD").split(",")
        login_raw = os.getenv("MT5_LOGIN", "").strip()
        mt5_login = int(login_raw) if login_raw.isdigit() else 0

        interval_raw = os.getenv("MT5_TICK_INTERVAL_MS", "").strip()
        tick_interval_ms = int(interval_raw) if interval_raw.isdigit() else 100

        return cls(
            server_url=os.getenv("TRADEGEAR_SERVER_URL", "ws://localhost:8001/ws/agent"),
            agent_token=os.getenv("TRADEGEAR_AGENT_TOKEN", "dev-agent-secret"),
            mt5_login=mt5_login,
            mt5_password=os.getenv("MT5_PASSWORD", ""),
            mt5_server=os.getenv("MT5_SERVER", ""),
            mt5_path=os.getenv("MT5_PATH", ""),
            tick_symbols=[s.strip().upper() for s in symbols],
            tick_interval_ms=tick_interval_ms,
        )
