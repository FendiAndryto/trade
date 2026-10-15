export interface User {
  id: string;
  email: string;
  display_name: string;
  plan: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AccountSummary {
  login?: number | null;
  server?: string | null;
  broker?: string | null;
  currency?: string | null;
  balance: number;
  equity: number;
  floating_pnl: number;
  margin_used: number;
  margin_level: number | null;
  mt5_status: "connected" | "disconnected" | "error";
}

export interface TradingSummary {
  total_trades_today: number;
  winning_trades_today: number;
  losing_trades_today: number;
  pnl_today: number;
  win_rate_today: number;
  daily_loss_limit_pct: number;
  daily_loss_used_pct: number;
  open_trades_count: number;
  max_concurrent_trades: number;
}

export interface DashboardSummary {
  account: AccountSummary;
  trading: TradingSummary;
}

export interface Trade {
  id: string;
  mt5_ticket?: number | null;
  symbol: string;
  direction: "buy" | "sell" | "BUY" | "SELL";
  lot?: number;
  lot_size?: number;
  open_price?: number;
  entry_price?: number | null;
  close_price?: number | null;
  sl_price?: number | null;
  stop_loss?: number | null;
  tp_price?: number | null;
  take_profit?: number | null;
  pnl?: number | null;
  realized_pnl?: number | null;
  status: "pending" | "open" | "closed" | "rejected" | "cancelled" | "PENDING" | "OPEN" | "CLOSED" | "FAILED";
  opened_at?: string | null;
  closed_at?: string | null;
  comment?: string;
}

export interface RiskProfile {
  risk_per_trade_pct: number;
  daily_loss_limit_pct: number;
  max_concurrent_trades: number;
  max_lot_size: number;
  min_lot_size: number;
  session_filter?: Record<string, unknown> | null;
  advanced_rules?: Record<string, unknown> | null;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  webhook_url: string;
  risk_profile?: RiskProfile | null;
  created_at: string;
}

export interface WebhookLog {
  id: string;
  strategy_id: string;
  raw_payload: Record<string, unknown>;
  status: "received" | "validated" | "executed" | "rejected" | "failed";
  rejection_reason?: string | null;
  processing_ms: number;
  created_at: string;
}

export interface EquityPoint {
  date: string;
  equity: number;
  balance: number;
  pnl: number;
}

export interface EquityCurveResponse {
  data: EquityPoint[];
}

export interface DailyStatItem {
  date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: number;
  max_drawdown: number;
  win_rate: number;
  daily_limit_hit: boolean;
}

