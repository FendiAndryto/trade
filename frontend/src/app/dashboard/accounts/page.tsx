"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

export default function AccountsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [copied, setCopied] = useState(false);
  const { isConnected, accountUpdate } = useWebSocket();

  useEffect(() => {
    api.dashboard.getSummary().then(setSummary).catch(() => null);
  }, []);

  const balance = accountUpdate?.balance ?? summary?.account.balance ?? 0;
  const equity = accountUpdate?.equity ?? summary?.account.equity ?? 0;
  const floatingPnl = equity - balance;
  const login = accountUpdate?.login ?? summary?.account.login ?? null;
  const server = accountUpdate?.server ?? summary?.account.server ?? null;
  const broker = accountUpdate?.company ?? summary?.account.broker ?? null;

  const envSnippet = `# TradeGear Windows MT5 Agent (.env)
# Leave blank to auto-connect to currently active MT5 terminal
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
MT5_PATH=
TRADEGEAR_SERVER_URL=wss://trade.homever.my.id/ws/agent
TRADEGEAR_AGENT_TOKEN=dev-agent-secret`;

  const copyConfig = () => {
    navigator.clipboard.writeText(envSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1>MetaTrader 5 Account Bridge</h1>
        <p>Monitor your active MT5 terminal connection and configure Windows Bridge Agents</p>
      </div>

      <div className={styles.accountsGrid}>
        {/* Active MT5 Account */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Terminal Status</span>
            <span className={`badge ${isConnected ? "badge-success" : "badge-secondary"}`}>
              <span
                className={`pulse-dot ${
                  isConnected ? "pulse-dot-green" : "pulse-dot-red"
                }`}
                style={{ width: 6, height: 6 }}
              />
              {isConnected ? "Connected (Live)" : "Disconnected"}
            </span>
          </div>

          <div className={styles.accountDetails}>
            <div className={styles.detailRow}>
              <span className="text-muted">Account Number</span>
              <span className="mono" style={{ fontWeight: 600 }}>
                {login ? `#${login}` : "Not Connected"}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Broker Server</span>
              <span>{server || "—"}</span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Broker Name</span>
              <span>{broker || "—"}</span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Balance</span>
              <span className="mono">${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Equity</span>
              <span className="mono text-success" style={{ fontWeight: 600 }}>
                ${equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Floating P&L</span>
              <span
                className={`mono ${floatingPnl >= 0 ? "profit" : "loss"}`}
                style={{ fontWeight: 600 }}
              >
                {floatingPnl >= 0 ? "+" : ""}${floatingPnl.toFixed(2)}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Account Type</span>
              <span className="badge badge-info">Hedging / Real-time</span>
            </div>
          </div>
        </div>

        {/* MT5 Agent Bridge Instructions */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Windows Bridge Setup</span>
            <button className="btn btn-secondary btn-sm" onClick={copyConfig}>
              {copied ? "✓ Copied!" : "Copy Config"}
            </button>
          </div>

          <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            To execute trades on MetaTrader 5, run the local Python agent on your Windows PC with the MT5 terminal installed:
          </p>

          <pre className={styles.codeBlock}>{envSnippet}</pre>

          <div style={{ marginTop: "16px" }}>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
              Run command in <code>TRADING/mt5-agent</code>:
            </span>
            <pre
              className={styles.codeBlock}
              style={{ color: "var(--text-primary)", background: "var(--bg-elevated)", marginTop: "6px" }}
            >
              python -m agent.main
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
