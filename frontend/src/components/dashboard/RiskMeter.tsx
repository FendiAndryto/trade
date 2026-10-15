"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { DashboardSummary, Strategy } from "@/lib/types";
import styles from "./RiskMeter.module.css";

export default function RiskMeter() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activeStrategy, setActiveStrategy] = useState<Strategy | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [sum, strats] = await Promise.all([
        api.dashboard.getSummary().catch(() => null),
        api.strategies.list().catch(() => []),
      ]);
      if (sum) setSummary(sum);
      if (strats && strats.length > 0) {
        const active = strats.find((s) => s.is_active) || strats[0];
        setActiveStrategy(active);
      }
    } catch {
      // Fallback
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const dailyLossUsed = summary?.trading.daily_loss_used_pct ?? 0.0;
  const dailyLossLimit = summary?.trading.daily_loss_limit_pct ?? 3.0;
  const openTrades = summary?.trading.open_trades_count ?? 0;
  const maxTrades = summary?.trading.max_concurrent_trades ?? 3;

  const riskPerTrade = activeStrategy?.risk_profile?.risk_per_trade_pct ?? 1.0;
  const maxLot = activeStrategy?.risk_profile?.max_lot_size ?? 1.0;
  const strategyName = activeStrategy?.name ?? "Gold Scalper Pro XAUUSD";

  const lossRatio = dailyLossLimit > 0 ? (dailyLossUsed / dailyLossLimit) * 100 : 0;
  const tradeRatio = maxTrades > 0 ? (openTrades / maxTrades) * 100 : 0;

  const isLimitHit = lossRatio >= 100;
  const isWarning = lossRatio >= 70 || tradeRatio >= 90;

  const getBarColor = (ratio: number) => {
    if (ratio >= 90) return "var(--color-danger)";
    if (ratio >= 70) return "var(--color-warning)";
    return "var(--color-success)";
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Risk Monitor</span>
        <span
          className={`badge ${
            isLimitHit
              ? "badge-danger"
              : isWarning
              ? "badge-warning"
              : "badge-success"
          }`}
        >
          <span
            className={`pulse-dot ${
              isLimitHit
                ? "pulse-dot-red"
                : isWarning
                ? "pulse-dot-amber"
                : "pulse-dot-green"
            }`}
            style={{ width: 6, height: 6 }}
          />
          {isLimitHit ? "Limit Breached" : isWarning ? "Elevated Risk" : "Safe"}
        </span>
      </div>

      <div className={styles.meters}>
        {/* Daily Loss Meter */}
        <div className={styles.meterItem}>
          <div className={styles.meterHeader}>
            <span className={styles.meterLabel}>Daily Loss</span>
            <span className={`${styles.meterValue} mono`}>
              {dailyLossUsed.toFixed(1)}% / {dailyLossLimit}%
            </span>
          </div>
          <div className={styles.meterBar}>
            <div
              className={styles.meterFill}
              style={{
                width: `${Math.min(Math.max(lossRatio, 2), 100)}%`,
                background: getBarColor(lossRatio),
                boxShadow: `0 0 8px ${getBarColor(lossRatio)}`,
              }}
            />
          </div>
        </div>

        {/* Open Trades Meter */}
        <div className={styles.meterItem}>
          <div className={styles.meterHeader}>
            <span className={styles.meterLabel}>Open Trades</span>
            <span className={`${styles.meterValue} mono`}>
              {openTrades} / {maxTrades}
            </span>
          </div>
          <div className={styles.meterBar}>
            <div
              className={styles.meterFill}
              style={{
                width: `${Math.min(tradeRatio, 100)}%`,
                background: getBarColor(tradeRatio),
                boxShadow: `0 0 8px ${getBarColor(tradeRatio)}`,
              }}
            />
          </div>
        </div>

        {/* Risk per trade */}
        <div className={styles.infoRow}>
          <span className="text-muted">Risk per Trade</span>
          <span className="mono">{riskPerTrade.toFixed(1)}%</span>
        </div>
        <div className={styles.infoRow}>
          <span className="text-muted">Max Lot Bound</span>
          <span className="mono">{maxLot.toFixed(2)} lots</span>
        </div>
        <div className={styles.infoRow}>
          <span className="text-muted">Active Strategy</span>
          <span
            style={{
              color: "var(--accent-blue)",
              fontWeight: 600,
              maxWidth: "160px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={strategyName}
          >
            {strategyName}
          </span>
        </div>
      </div>
    </div>
  );
}

