"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { WebhookLogItem, useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

interface LogDetail {
  id: string;
  strategy_id?: string;
  action: string;
  symbol: string;
  status: string;
  message: string;
  processing_ms: number;
  received_at: string;
  raw_payload?: any;
}

export default function WebhookLogsPage() {
  const [filter, setFilter] = useState<"all" | "executed" | "rejected">("all");
  const [logs, setLogs] = useState<LogDetail[]>([]);
  const [selectedPayload, setSelectedPayload] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { recentWebhooks } = useWebSocket();

  const fetchLogs = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.dashboard.getWebhooks(50);
      if (res && Array.isArray(res) && res.length > 0) {
        const mapped: LogDetail[] = res.map((l: any) => ({
          id: l.id,
          strategy_id: l.strategy_id,
          action: l.raw_payload?.action?.toUpperCase() || "ALERT",
          symbol: l.raw_payload?.symbol?.toUpperCase() || "XAUUSD",
          status: l.status?.toLowerCase() || "executed",
          message:
            l.rejection_reason ||
            l.raw_payload?.comment ||
            "Signal processed successfully",
          processing_ms: l.processing_ms ?? 35,
          received_at: l.received_at,
          raw_payload: l.raw_payload,
        }));
        setLogs(mapped);
      }
    } catch {
      // Use websocket stream as fallback
      if (recentWebhooks.length > 0) {
        setLogs(recentWebhooks as LogDetail[]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [recentWebhooks]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const filteredLogs = logs.filter((l) => {
    if (filter === "executed") return l.status === "executed";
    if (filter === "rejected") return l.status === "rejected";
    return true;
  });

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.titleArea}>
          <h1>TradingView Webhook Logs</h1>
          <p>Real-time audit log of incoming TradingView alerts and execution pipeline</p>
        </div>

        <div className={styles.filterBar}>
          {(["all", "executed", "rejected"] as const).map((mode) => (
            <button
              key={mode}
              className={`${styles.filterBtn} ${
                filter === mode ? styles.filterActive : ""
              }`}
              onClick={() => setFilter(mode)}
            >
              {mode.toUpperCase()} ({logs.filter((l) => mode === "all" || l.status === mode).length})
            </button>
          ))}
        </div>
      </div>

      {/* Logs Table */}
      <div className={`card ${styles.logsCard}`}>
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Signal</th>
                <th>Symbol</th>
                <th>Status</th>
                <th>Processing Time</th>
                <th>Details / Reason</th>
                <th style={{ textAlign: "right" }}>Payload</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className={styles.emptyState}>
                    No {filter} webhook logs recorded.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const isBuy = log.action === "BUY";
                  const isExec = log.status === "executed";
                  const dateObj = new Date(log.received_at);
                  const timeFormatted = !isNaN(dateObj.getTime())
                    ? dateObj.toLocaleTimeString("en-GB", { hour12: false })
                    : log.received_at;

                  return (
                    <tr key={log.id}>
                      <td className="mono text-muted">{timeFormatted}</td>
                      <td>
                        <span
                          className={`badge ${
                            isBuy ? "badge-success" : "badge-danger"
                          }`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td>
                        <strong>{log.symbol}</strong>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isExec
                              ? "badge-success"
                              : log.status === "rejected"
                              ? "badge-danger"
                              : "badge-warning"
                          }`}
                        >
                          {log.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="mono text-muted">{log.processing_ms} ms</td>
                      <td style={{ color: "var(--text-secondary)", maxWidth: "340px" }}>
                        {log.message}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() =>
                            setSelectedPayload(
                              log.raw_payload || {
                                action: log.action,
                                symbol: log.symbol,
                                time: log.received_at,
                              }
                            )
                          }
                        >
                          View JSON
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Payload Modal */}
      {selectedPayload && (
        <div className={styles.payloadModal}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <span className="card-title">TradingView Webhook Payload</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setSelectedPayload(null)}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalBody}>
              <pre className={styles.jsonBox}>
                {JSON.stringify(selectedPayload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
