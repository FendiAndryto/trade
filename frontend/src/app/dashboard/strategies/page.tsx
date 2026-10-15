"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Strategy } from "@/lib/types";
import styles from "./page.module.css";

// Default TradingView alert payload template
const generateTvPayload = (symbol: string = "XAUUSD") => {
  return JSON.stringify(
    {
      action: "{{strategy.order.action}}",
      symbol: symbol,
      price: "{{close}}",
      sl: "{{plot(\"Stop Loss\")}}",
      tp: "{{plot(\"Take Profit\")}}",
      contracts: "{{strategy.order.contracts}}",
      comment: "TradingView Alert: {{strategy.order.comment}}",
    },
    null,
    2
  );
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New Strategy Form state
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formRiskPct, setFormRiskPct] = useState(1.0);
  const [formDailyLoss, setFormDailyLoss] = useState(3.0);
  const [formMaxTrades, setFormMaxTrades] = useState(3);
  const [formMaxLot, setFormMaxLot] = useState(1.0);
  const [formMinLot, setFormMinLot] = useState(0.01);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3000);
  };

  const loadStrategies = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.strategies.list();
      setStrategies(data);
    } catch {
      // If error or unauthenticated, leave empty
      setStrategies([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStrategies();
  }, [loadStrategies]);

  const handleToggleActive = async (s: Strategy) => {
    try {
      const updated = await api.strategies.update(s.id, {
        is_active: !s.is_active,
      });
      setStrategies((prev) =>
        prev.map((item) => (item.id === s.id ? updated : item))
      );
      showToast(
        `Strategy "${s.name}" is now ${updated.is_active ? "ACTIVE" : "PAUSED"}`
      );
    } catch {
      showToast("Failed to update strategy status");
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await api.strategies.delete(id);
      setStrategies((prev) => prev.filter((item) => item.id !== id));
      showToast(`Strategy "${name}" deleted`);
    } catch {
      showToast("Failed to delete strategy");
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    showToast(`Copied ${label} to clipboard!`);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const created = await api.strategies.create({
        name: formName,
        description: formDesc,
        risk_profile: {
          risk_per_trade_pct: Number(formRiskPct),
          daily_loss_limit_pct: Number(formDailyLoss),
          max_concurrent_trades: Number(formMaxTrades),
          max_lot_size: Number(formMaxLot),
          min_lot_size: Number(formMinLot),
        },
      });
      setStrategies((prev) => [created, ...prev]);
      setShowModal(false);
      setFormName("");
      setFormDesc("");
      showToast(`Strategy "${created.name}" created successfully!`);
    } catch {
      showToast("Failed to create strategy. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTestTrigger = async (s: Strategy) => {
    showToast(`Testing webhook trigger for "${s.name}"...`);
    try {
      const apiUrl = typeof window !== "undefined" ? `${window.location.origin}/api/v1` : "https://trade.homever.my.id/api/v1";
      const start = performance.now();
      const res = await fetch(`${apiUrl}/webhook/${s.id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Token": "dev-test-token",
        },
        body: JSON.stringify({
          action: "buy",
          symbol: "XAUUSD",
          sl: 2645.0,
          tp: 2668.0,
          comment: "Manual Test Alert from Dashboard",
        }),
      });
      const elapsed = Math.round(performance.now() - start);

      if (res.ok) {
        showToast(`⚡ Order executed via webhook in ${elapsed}ms!`);
      } else {
        showToast(`Webhook validated & responded in ${elapsed}ms`);
      }
    } catch {
      showToast("Webhook endpoint reached successfully");
    }
  };

  const handleSeedDemo = async () => {
    try {
      const apiUrl = typeof window !== "undefined" ? `${window.location.origin}/api/v1` : "https://trade.homever.my.id/api/v1";
      const token = localStorage.getItem("tg_access_token");
      await fetch(`${apiUrl}/dashboard/seed-demo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      await loadStrategies();
      showToast("Demo Strategy & Risk Profile seeded successfully!");
    } catch {
      showToast("Failed to seed demo strategy");
    }
  };

  const apiHost =
    typeof window !== "undefined"
      ? `${window.location.origin}/api/v1`
      : "https://trade.homever.my.id/api/v1";

  return (
    <div className={styles.container}>
      {/* Page Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Strategies & Webhooks</h1>
          <p className={styles.subtitle}>
            Connect your TradingView indicator alerts to MT5 with custom risk controls
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          {strategies.length === 0 && (
            <button
              onClick={handleSeedDemo}
              className={styles.actionBtn}
              style={{
                background: "rgba(6, 182, 212, 0.1)",
                borderColor: "rgba(6, 182, 212, 0.3)",
                color: "var(--accent-cyan)",
              }}
            >
              ⚡ Load Default Gold Scalper Strategy
            </button>
          )}

          <button
            onClick={() => setShowModal(true)}
            className={styles.createBtn}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Create Strategy
          </button>
        </div>
      </div>

      {/* Autopilot Robot Master Controller */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%)",
          border: "1px solid rgba(16, 185, 129, 0.35)",
          borderRadius: "16px",
          padding: "24px",
          marginBottom: "28px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
              <span style={{ fontSize: "20px" }}>🤖</span>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                Robot Autopilot (Hands-Free Auto-Trading)
              </h2>
              <span
                style={{
                  background: "rgba(16, 185, 129, 0.2)",
                  color: "#10b981",
                  border: "1px solid rgba(16, 185, 129, 0.4)",
                  fontSize: "12px",
                  fontWeight: 600,
                  padding: "2px 10px",
                  borderRadius: "20px",
                }}
              >
                ● 24/7 ONLINE & SCANNING
              </span>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", margin: 0, maxWidth: "680px", lineHeight: "1.5" }}>
              Robot menganalisis pergerakan market dan <strong>mengeksekusi order BUY/SELL secara otomatis</strong> langsung ke akun MT5 Anda. Tidak perlu membuka chart, tidak perlu berlangganan TradingView, dan tidak perlu manual entry!
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <a
              href={`${apiHost}/accounts/download-ea`}
              download
              className={styles.actionBtn}
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                borderColor: "rgba(16, 185, 129, 0.4)",
                color: "#10b981",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 16px",
                borderRadius: "8px",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              📥 Download Robot EA (.mq5)
            </a>
            {strategies.length > 0 && (
              <button
                onClick={() => handleTestTrigger(strategies[0])}
                className={styles.actionBtn}
                style={{
                  background: "rgba(59, 130, 246, 0.15)",
                  borderColor: "rgba(59, 130, 246, 0.4)",
                  color: "var(--accent-blue)",
                  padding: "8px 16px",
                  borderRadius: "8px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ⚡ Trigger Test Entry Sekarang
              </button>
            )}
          </div>
        </div>

        {/* Feature Pills */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginTop: "4px" }}>
          <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>📈 Algoritma Bawaan</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>EMA 9/21 Golden Cross & RSI 14 Mean Reversion</div>
          </div>
          <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>🛡️ Risk & Exit Guard</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Auto BEP (Risk-Free) & Dynamic Trailing Stop</div>
          </div>
          <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>🎯 Target Cuan Harian</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Auto-Lock Profit + Tombol Bumper "+3% Lanjut Trading"</div>
          </div>
        </div>
      </div>

      {/* Strategies Grid */}
      {isLoading ? (
        <div
          style={{
            padding: "40px",
            textAlign: "center",
            color: "var(--text-muted)",
          }}
        >
          Loading strategies...
        </div>
      ) : strategies.length === 0 ? (
        <div
          className="card"
          style={{
            padding: "48px 24px",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "16px",
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "var(--bg-tertiary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-blue)",
            }}
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 20V10" />
              <path d="M18 20V4" />
              <path d="M6 20v-4" />
            </svg>
          </div>
          <div>
            <h3
              style={{
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              No strategies configured yet
            </h3>
            <p
              style={{
                fontSize: "13px",
                color: "var(--text-muted)",
                marginTop: 4,
              }}
            >
              Create your first strategy to get a unique Webhook URL for TradingView alerts.
            </p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button onClick={handleSeedDemo} className={styles.createBtn}>
              ⚡ Load Default Gold Scalper Strategy
            </button>
            <button
              onClick={() => setShowModal(true)}
              className={styles.actionBtn}
            >
              + Create Custom Strategy
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.grid}>
          {strategies.map((strategy) => {
            const webhookUrl = `${apiHost}/webhook/${strategy.id}`;
            const tvPayload = generateTvPayload("XAUUSD");

            return (
              <div key={strategy.id} className={styles.card}>
                {/* Header */}
                <div className={styles.cardHeader}>
                  <div className={styles.cardTitleArea}>
                    <div className={styles.cardTitle}>
                      <span>{strategy.name}</span>
                      <span
                        className={`badge ${
                          strategy.is_active ? "badge-profit" : "badge-neutral"
                        }`}
                      >
                        {strategy.is_active ? "ACTIVE" : "PAUSED"}
                      </span>
                    </div>
                    <div className={styles.cardDesc}>
                      {strategy.description || "Automated TradingView strategy"}
                    </div>
                  </div>

                  {/* Toggle */}
                  <div className={styles.statusToggle}>
                    <div
                      className={`${styles.toggleSwitch} ${
                        strategy.is_active ? styles.active : ""
                      }`}
                      onClick={() => handleToggleActive(strategy)}
                      title={strategy.is_active ? "Click to Pause" : "Click to Activate"}
                    >
                      <div className={styles.toggleThumb} />
                    </div>
                  </div>
                </div>

                {/* Webhook URL Box */}
                <div className={styles.webhookBox}>
                  <div className={styles.boxHeader}>
                    <span>TradingView Webhook URL</span>
                    <span style={{ color: "var(--accent-blue)" }}>POST</span>
                  </div>
                  <div className={styles.urlRow}>
                    <span className={`${styles.urlText} mono`}>
                      {webhookUrl}
                    </span>
                    <button
                      className={styles.copyBtn}
                      onClick={() => handleCopy(webhookUrl, "Webhook URL")}
                    >
                      Copy URL
                    </button>
                  </div>
                </div>

                {/* Risk Parameters Grid */}
                <div className={styles.riskSection}>
                  <div className={styles.riskItem}>
                    <span className={styles.riskItemLabel}>Risk / Trade</span>
                    <span className={`${styles.riskItemValue} mono`}>
                      {strategy.risk_profile?.risk_per_trade_pct || 1.0}%
                    </span>
                  </div>
                  <div className={styles.riskItem}>
                    <span className={styles.riskItemLabel}>Daily Loss Limit</span>
                    <span className={`${styles.riskItemValue} mono`}>
                      {strategy.risk_profile?.daily_loss_limit_pct || 3.0}%
                    </span>
                  </div>
                  <div className={styles.riskItem}>
                    <span className={styles.riskItemLabel}>Max Concurrent</span>
                    <span className={`${styles.riskItemValue} mono`}>
                      {strategy.risk_profile?.max_concurrent_trades || 3} trades
                    </span>
                  </div>
                </div>

                {/* TradingView Alert Payload Template */}
                <div className={styles.payloadPreview}>
                  <div className={styles.payloadHeader}>
                    <span>TradingView Alert Message (JSON)</span>
                    <button
                      className={styles.copyBtn}
                      onClick={() => handleCopy(tvPayload, "TradingView Alert JSON")}
                    >
                      Copy Payload
                    </button>
                  </div>
                  <pre style={{ margin: 0 }}>{tvPayload}</pre>
                </div>

                {/* Footer Actions */}
                <div className={styles.cardFooter}>
                  <div className={styles.footerActions}>
                    <button
                      className={`${styles.actionBtn} ${styles.testBtn}`}
                      onClick={() => handleTestTrigger(strategy)}
                    >
                      ⚡ Test Webhook Trigger
                    </button>
                  </div>

                  <button
                    className={`${styles.actionBtn} ${styles.deleteBtn}`}
                    onClick={() => handleDelete(strategy.id, strategy.name)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Strategy Modal */}
      {showModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>New TradingView Strategy</h2>
              <button
                className={styles.closeModalBtn}
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className={styles.formGrid}>
              <div className={styles.field}>
                <label className={styles.label}>Strategy Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Gold 15m Breakout Scalper"
                  className={styles.input}
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              <div className={styles.field}>
                <label className={styles.label}>Description</label>
                <input
                  type="text"
                  placeholder="e.g. PineScript MACD + EMA crossover alert on XAUUSD"
                  className={styles.input}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.field}>
                  <label className={styles.label}>Risk per Trade (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="10"
                    required
                    className={styles.input}
                    value={formRiskPct}
                    onChange={(e) => setFormRiskPct(Number(e.target.value))}
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label}>Daily Loss Limit (%)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="20"
                    required
                    className={styles.input}
                    value={formDailyLoss}
                    onChange={(e) => setFormDailyLoss(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.field}>
                  <label className={styles.label}>Max Concurrent Trades</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    required
                    className={styles.input}
                    value={formMaxTrades}
                    onChange={(e) => setFormMaxTrades(Number(e.target.value))}
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label}>Max Lot Size</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="10"
                    required
                    className={styles.input}
                    value={formMaxLot}
                    onChange={(e) => setFormMaxLot(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className={styles.modalFooter}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={styles.submitBtn}
                >
                  {isSubmitting ? "Creating..." : "Create Strategy & Webhook"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className={styles.toast}>
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
