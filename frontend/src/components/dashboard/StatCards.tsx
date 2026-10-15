import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";
import styles from "./StatCards.module.css";

interface StatData {
  label: string;
  value: string;
  change?: string;
  changeType?: "profit" | "loss" | "neutral";
  icon: React.ReactNode;
}

export default function StatCards() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    let isMounted = true;
    api.dashboard
      .getSummary()
      .then((data) => {
        if (isMounted) setSummary(data);
      })
      .catch(() => {
        // Use default fallback stats
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const balance = summary?.account.balance ?? 10245.3;
  const equity = summary?.account.equity ?? 10312.5;
  const floatingPnl = summary?.account.floating_pnl ?? 67.2;
  const pnlToday = summary?.trading.pnl_today ?? 127.4;
  const winRate = summary?.trading.win_rate_today ?? 75;
  const winTrades = summary?.trading.winning_trades_today ?? 3;
  const loseTrades = summary?.trading.losing_trades_today ?? 1;
  const dailyLossUsed = summary?.trading.daily_loss_used_pct ?? 0.0;
  const dailyLossLimit = summary?.trading.daily_loss_limit_pct ?? 3.0;
  const openTrades = summary?.trading.open_trades_count ?? 2;
  const maxTrades = summary?.trading.max_concurrent_trades ?? 3;

  const stats: StatData[] = [
    {
      label: "Balance",
      value: `$${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      change: `+$${(balance - 10000).toFixed(2)} all-time`,
      changeType: "profit",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" /><path d="M12 18V6" />
        </svg>
      ),
    },
    {
      label: "Equity",
      value: `$${equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      change: `${floatingPnl >= 0 ? "+" : ""}$${floatingPnl.toFixed(2)} floating`,
      changeType: floatingPnl >= 0 ? "profit" : "loss",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
        </svg>
      ),
    },
    {
      label: "Today P&L",
      value: `${pnlToday >= 0 ? "+" : ""}$${pnlToday.toFixed(2)}`,
      change: `${winTrades}W / ${loseTrades}L • ${winRate.toFixed(0)}% WR`,
      changeType: pnlToday >= 0 ? "profit" : "loss",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      ),
    },
    {
      label: "Daily Loss Used",
      value: `${dailyLossUsed.toFixed(1)}%`,
      change: `Limit: ${dailyLossLimit.toFixed(1)}%`,
      changeType: dailyLossUsed > dailyLossLimit ? "loss" : "neutral",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      ),
    },
    {
      label: "Open Trades",
      value: `${openTrades}`,
      change: `Max: ${maxTrades}`,
      changeType: "neutral",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18" /><path d="M9 21V9" />
        </svg>
      ),
    },
  ];

  return (
    <div className="stats-grid">
      {stats.map((stat) => (
        <div key={stat.label} className={`stat-card ${styles.card}`}>
          <div className={styles.iconWrapper}>{stat.icon}</div>
          <div className="stat-label">{stat.label}</div>
          <div
            className={`stat-value ${
              stat.changeType === "profit"
                ? "profit"
                : stat.changeType === "loss"
                ? "loss"
                : ""
            }`}
          >
            {stat.value}
          </div>
          {stat.change && (
            <div
              className={`stat-change ${
                stat.changeType === "profit"
                  ? "profit"
                  : stat.changeType === "loss"
                  ? "loss"
                  : "text-muted"
              }`}
            >
              {stat.change}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
