"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { DashboardSummary, Strategy } from "@/lib/types";
import styles from "./RiskMeter.module.css";

export default function RiskMeter() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activeStrategy, setActiveStrategy] = useState<Strategy | null>(null);
  const [profitTargetPct, setProfitTargetPct] = useState(5.0);
  const [isEditingTarget, setIsEditingTarget] = useState(false);
  const [customTarget, setCustomTarget] = useState("5.0");

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
        const rules = active.risk_profile?.advanced_rules as any;
        if (rules?.daily_profit_target_pct) {
          setProfitTargetPct(Number(rules.daily_profit_target_pct));
          setCustomTarget(String(rules.daily_profit_target_pct));
        }
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
  const pnlToday = summary?.trading.pnl_today ?? 0.0;
  const balance = summary?.account.balance ?? 10000.0;

  const currentProfitPct = balance > 0 && pnlToday > 0 ? (pnlToday / balance) * 100 : 0.0;
  const profitTargetRatio = profitTargetPct > 0 ? (currentProfitPct / profitTargetPct) * 100 : 0;
  const isTargetAchieved = profitTargetRatio >= 100;

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

  const handleBumpTarget = async (increment: number) => {
    const newTarget = profitTargetPct + increment;
    setProfitTargetPct(newTarget);
    setCustomTarget(newTarget.toFixed(1));
    if (activeStrategy) {
      try {
        await api.strategies.updateRisk(activeStrategy.id, {
          advanced_rules: {
            ...(activeStrategy.risk_profile?.advanced_rules || {}),
            daily_profit_target_pct: newTarget,
            auto_bep_enabled: true,
          },
        });
      } catch {
        // Optimistic UI
      }
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Risk & Profit Guard</span>
        <span
          className={`badge ${
            isTargetAchieved
              ? "badge-info"
              : isLimitHit
              ? "badge-danger"
              : isWarning
              ? "badge-warning"
              : "badge-success"
          }`}
        >
          <span
            className={`pulse-dot ${
              isTargetAchieved
                ? "pulse-dot-green"
                : isLimitHit
                ? "pulse-dot-red"
                : isWarning
                ? "pulse-dot-amber"
                : "pulse-dot-green"
            }`}
            style={{ width: 6, height: 6 }}
          />
          {isTargetAchieved
            ? "Target Cuan Hit 🎯"
            : isLimitHit
            ? "Limit Breached"
            : isWarning
            ? "Elevated Risk"
            : "Safe"}
        </span>
      </div>

      <div className={styles.meters}>
        {/* Daily Profit Target Meter with Target Bumper */}
        <div className={styles.meterItem}>
          <div className={styles.meterHeader}>
            <span className={styles.meterLabel} style={{ color: "#34d399", fontWeight: 600 }}>
              🎯 Target Cuan Harian
            </span>
            <span className={`${styles.meterValue} mono`} style={{ color: "#34d399" }}>
              +{currentProfitPct.toFixed(1)}% / +{profitTargetPct.toFixed(1)}%
            </span>
          </div>
          <div className={styles.meterBar}>
            <div
              className={styles.meterFill}
              style={{
                width: `${Math.min(Math.max(profitTargetRatio, 2), 100)}%`,
                background: "#10b981",
                boxShadow: "0 0 8px rgba(16, 185, 129, 0.5)",
              }}
            />
          </div>

          {/* Target Bumper Button when hit or close */}
          <div style={{ marginTop: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              {isTargetAchieved ? "Target hari ini tercapai!" : "Ingin tambah target hari ini?"}
            </span>
            <button
              onClick={() => handleBumpTarget(3.0)}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-primary)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-primary)",
                fontSize: "11px",
                fontWeight: 600,
                padding: "2px 8px",
                cursor: "pointer",
              }}
              title="Naikkan target profit 3% lagi untuk lanjut trading hari ini"
            >
              +3% Lanjut Trading
            </button>
          </div>
        </div>

        {/* Daily Loss Meter */}
        <div className={styles.meterItem}>
          <div className={styles.meterHeader}>
            <span className={styles.meterLabel}>Daily Loss Limit</span>
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

        {/* Protections Badges */}
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
          <span className="badge badge-info" style={{ fontSize: "10px" }}>
            🛡️ Auto BEP (Risk-Free)
          </span>
          <span className="badge badge-info" style={{ fontSize: "10px" }}>
            ⚡ Trailing Stop
          </span>
          <span className="badge badge-info" style={{ fontSize: "10px" }}>
            🛑 Max Spread Guard
          </span>
        </div>

        {/* Risk per trade info */}
        <div className={styles.infoRow} style={{ marginTop: "6px" }}>
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
