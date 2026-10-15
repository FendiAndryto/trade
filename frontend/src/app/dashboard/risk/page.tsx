"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Strategy, RiskProfile, DashboardSummary } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

export default function RiskPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  // Form State
  const [riskPct, setRiskPct] = useState(1.0);
  const [dailyLossPct, setDailyLossPct] = useState(3.0);
  const [maxTrades, setMaxTrades] = useState(3);
  const [maxLot, setMaxLot] = useState(1.0);
  const [minLot, setMinLot] = useState(0.01);
  const [isSaving, setIsSaving] = useState(false);
  const [isEmergencyClosing, setIsEmergencyClosing] = useState(false);

  const { addToast } = useWebSocket();

  const loadData = useCallback(async () => {
    try {
      const [strats, sum] = await Promise.all([
        api.strategies.list().catch(() => []),
        api.dashboard.getSummary().catch(() => null),
      ]);
      if (strats.length > 0) {
        setStrategies(strats);
        const active = strats.find((s) => s.is_active) || strats[0];
        setSelectedStrategyId(active.id);
        if (active.risk_profile) {
          setRiskPct(active.risk_profile.risk_per_trade_pct);
          setDailyLossPct(active.risk_profile.daily_loss_limit_pct);
          setMaxTrades(active.risk_profile.max_concurrent_trades);
          setMaxLot(active.risk_profile.max_lot_size);
          setMinLot(active.risk_profile.min_lot_size);
        }
      }
      if (sum) setSummary(sum);
    } catch {
      // Keep fallbacks
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStrategyChange = (id: string) => {
    setSelectedStrategyId(id);
    const s = strategies.find((item) => item.id === id);
    if (s && s.risk_profile) {
      setRiskPct(s.risk_profile.risk_per_trade_pct);
      setDailyLossPct(s.risk_profile.daily_loss_limit_pct);
      setMaxTrades(s.risk_profile.max_concurrent_trades);
      setMaxLot(s.risk_profile.max_lot_size);
      setMinLot(s.risk_profile.min_lot_size);
    }
  };

  const handleSaveRisk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStrategyId) return;

    setIsSaving(true);
    try {
      const updatedProfile: RiskProfile = {
        risk_per_trade_pct: Number(riskPct),
        daily_loss_limit_pct: Number(dailyLossPct),
        max_concurrent_trades: Number(maxTrades),
        max_lot_size: Number(maxLot),
        min_lot_size: Number(minLot),
      };

      await api.strategies.updateRisk(selectedStrategyId, updatedProfile);
      addToast({
        title: "Risk Parameters Saved",
        message: "New risk constraints have been updated and are live.",
        type: "success",
      });
    } catch {
      addToast({
        title: "Save Failed",
        message: "Failed to persist risk settings to database.",
        type: "danger",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleEmergencyCloseAll = async () => {
    if (!confirm("⚠️ EMERGENCY KILL-SWITCH: Are you sure you want to close ALL active positions across MT5?")) {
      return;
    }

    setIsEmergencyClosing(true);
    try {
      const openTrades = await api.trades.list({ status: "open" });
      if (openTrades && openTrades.trades) {
        for (const t of openTrades.trades) {
          await api.trades.close(t.id).catch(() => null);
        }
      }
      addToast({
        title: "Emergency Kill-Switch Triggered",
        message: "Sent batch close commands for all open MT5 positions.",
        type: "warning",
      });
    } catch {
      addToast({
        title: "Kill Switch Error",
        message: "Could not execute emergency close orders.",
        type: "danger",
      });
    } finally {
      setIsEmergencyClosing(false);
    }
  };

  const balance = summary?.account.balance ?? 10245.3;
  const maxRiskDollar = (balance * (riskPct / 100)).toFixed(2);
  const maxDailyLossDollar = (balance * (dailyLossPct / 100)).toFixed(2);

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1>Risk Management & Safety Guardrails</h1>
        <p>Set algorithmic position limits, loss caps, and circuit breakers for automated execution</p>
      </div>

      <div className={styles.riskGrid}>
        {/* Main Form */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Strategy Risk Parameters</span>
            {strategies.length > 0 && (
              <select
                className="input"
                style={{ width: "auto", padding: "6px 12px" }}
                value={selectedStrategyId}
                onChange={(e) => handleStrategyChange(e.target.value)}
              >
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <form onSubmit={handleSaveRisk}>
            <div className={styles.formGrid}>
              {/* Risk per trade */}
              <div className={styles.formGroup}>
                <label>Risk Per Trade (%)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  className="input mono"
                  value={riskPct}
                  onChange={(e) => setRiskPct(parseFloat(e.target.value) || 0)}
                  required
                />
                <span className={styles.helperText}>
                  Max loss ≈ <strong>${maxRiskDollar}</strong> per trade
                </span>
              </div>

              {/* Daily Loss Limit */}
              <div className={styles.formGroup}>
                <label>Daily Loss Limit (%)</label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  max="20"
                  className="input mono"
                  value={dailyLossPct}
                  onChange={(e) => setDailyLossPct(parseFloat(e.target.value) || 0)}
                  required
                />
                <span className={styles.helperText}>
                  Circuit breaker trips at <strong>-${maxDailyLossDollar}</strong> today
                </span>
              </div>

              {/* Max Concurrent Trades */}
              <div className={styles.formGroup}>
                <label>Max Open Trades</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  className="input mono"
                  value={maxTrades}
                  onChange={(e) => setMaxTrades(parseInt(e.target.value) || 1)}
                  required
                />
                <span className={styles.helperText}>
                  Rejects extra signals once limit is reached
                </span>
              </div>

              {/* Max Lot Size */}
              <div className={styles.formGroup}>
                <label>Max Lot Size Ceiling</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="100"
                  className="input mono"
                  value={maxLot}
                  onChange={(e) => setMaxLot(parseFloat(e.target.value) || 0.1)}
                  required
                />
                <span className={styles.helperText}>
                  Safety ceiling regardless of lot calculator
                </span>
              </div>

              {/* Min Lot Size */}
              <div className={styles.formGroup}>
                <label>Min Lot Size Floor</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="10"
                  className="input mono"
                  value={minLot}
                  onChange={(e) => setMinLot(parseFloat(e.target.value) || 0.01)}
                  required
                />
                <span className={styles.helperText}>Broker standard: 0.01 micro lot</span>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSaving}
              style={{ width: "100%", padding: "12px" }}
            >
              {isSaving ? "Saving Guardrails..." : "Save Risk Guardrails"}
            </button>
          </form>
        </div>

        {/* Emergency Circuit Breakers */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          <div className={`card ${styles.emergencyCard}`}>
            <div className="card-header">
              <span className="card-title text-danger">⚠️ Emergency Controls</span>
              <span className="badge badge-danger">Live Fire</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                Use these emergency override actions if a TradingView indicator misfires or high-impact volatility occurs.
              </p>

              <button
                className="btn btn-danger"
                style={{ width: "100%", padding: "12px", fontWeight: 700 }}
                disabled={isEmergencyClosing}
                onClick={handleEmergencyCloseAll}
              >
                {isEmergencyClosing ? "Closing All Positions..." : "🚨 Emergency Close All Open Trades"}
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Execution Mode</span>
              <span className="badge badge-success">Automated</span>
            </div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              <p>
                ✓ All webhook orders pass through the pre-trade risk check pipeline.
              </p>
              <p style={{ marginTop: "8px" }}>
                ✓ If daily loss reaches <strong>{dailyLossPct}%</strong>, all subsequent signals are rejected automatically until tomorrow 00:00 UTC.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
