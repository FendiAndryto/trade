"use client";

import Link from "next/link";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./RecentWebhooks.module.css";

const statusBadge: Record<string, string> = {
  executed: "badge-success",
  rejected: "badge-danger",
  received: "badge-info",
  failed: "badge-warning",
};

export default function RecentWebhooks() {
  const { recentWebhooks, isConnected } = useWebSocket();

  const formatTime = (isoString?: string) => {
    if (!isoString) return new Date().toLocaleTimeString();
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString("en-GB", { hour12: false });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="card-title">Recent Webhooks</span>
          <span
            className={`badge ${
              isConnected ? "badge-success" : "badge-secondary"
            }`}
            style={{ fontSize: "10px", padding: "2px 6px" }}
          >
            {isConnected ? "● Live Feed" : "Offline"}
          </span>
        </div>
        <Link href="/dashboard/logs" className="btn btn-ghost btn-sm">
          View All
        </Link>
      </div>

      <div className={styles.logsList}>
        {recentWebhooks.length === 0 ? (
          <div
            style={{
              padding: "24px 16px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "var(--text-xs)",
            }}
          >
            Waiting for TradingView alert webhooks...
          </div>
        ) : (
          recentWebhooks.slice(0, 7).map((log) => (
            <div
              key={log.id}
              className={styles.logRow}
              style={{
                transition: "background 0.3s ease",
              }}
            >
              <div className={styles.logTime}>
                <span className="mono text-muted">
                  {formatTime(log.received_at)}
                </span>
              </div>
              <div className={styles.logAction}>
                <span
                  className={`badge ${
                    log.action.toUpperCase() === "BUY"
                      ? "badge-success"
                      : "badge-danger"
                  }`}
                >
                  {log.action.toUpperCase()}
                </span>
                <span className={styles.logSymbol}>{log.symbol}</span>
              </div>
              <div className={styles.logMessage}>
                <span className="text-secondary">{log.message}</span>
              </div>
              <div className={styles.logMeta}>
                <span
                  className={`badge ${
                    statusBadge[log.status.toLowerCase()] || "badge-info"
                  }`}
                >
                  {log.status}
                </span>
                <span className="mono text-muted" style={{ fontSize: "10px" }}>
                  {log.processing_ms ?? 35}ms
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
