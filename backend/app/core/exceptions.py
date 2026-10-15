"""
Custom exception classes for TradeGear.
"""


class TradeGearException(Exception):  # noqa: N818
    """Base exception for all TradeGear errors."""

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(self.message)


class TradeRejected(TradeGearException):
    """Raised when a trade signal is rejected by risk rules or validation."""

    pass


class RiskLimitExceeded(TradeRejected):
    """Raised when a trade violates a risk management rule."""

    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(message)


class DailyLossLimitHit(RiskLimitExceeded):
    """Raised when the daily loss limit has been reached."""

    def __init__(self, current_loss_pct: float, limit_pct: float):
        self.current_loss_pct = current_loss_pct
        self.limit_pct = limit_pct
        super().__init__(
            rule="daily_loss_limit",
            message=(
                f"Daily loss limit reached: {current_loss_pct:.1f}% (limit: {limit_pct:.1f}%)"
            ),
        )


class MaxConcurrentTradesExceeded(RiskLimitExceeded):
    """Raised when max concurrent trades limit has been reached."""

    def __init__(self, current_count: int, max_count: int):
        super().__init__(
            rule="max_concurrent_trades",
            message=(f"Max concurrent trades reached: {current_count}/{max_count}"),
        )


class MT5AgentOffline(TradeGearException):
    """Raised when the MT5 agent is not connected."""

    def __init__(self, mt5_account_id: str):
        super().__init__(f"MT5 agent for account {mt5_account_id} is offline")


class WebhookValidationError(TradeGearException):
    """Raised when a webhook payload fails validation."""

    pass


class StrategyDisabled(TradeGearException):
    """Raised when trying to execute a trade on a disabled strategy."""

    pass
