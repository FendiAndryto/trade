"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Trade } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

const fallbackTrades: Trade[] = [
  {
    id: "demo-1",
    mt5_ticket: 4829104,
    symbol: "XAUUSD",
    direction: "buy",
    lot: 0.1,
    entry_price: 2648.5,
    sl_price: 2642.0,
    tp_price: 2665.0,
    realized_pnl: 0.0,
    status: "open",
    opened_at: new Date(Date.now() - 42 * 60000).toISOString(),
    comment: "Trend pullback entry",
  },
  {
    id: "demo-2",
    mt5_ticket: 4829105,
    symbol: "EURUSD",
    direction: "sell",
    lot: 0.2,
    entry_price: 1.0892,
    sl_price: 1.0915,
    tp_price: 1.084,
    realized_pnl: 0.0,
    status: "open",
    opened_at: new Date(Date.now() - 15 * 60000).toISOString(),
    comment: "Bearish pin bar",
  },
  {
    id: "demo-3",
    mt5_ticket: 4828901,
    symbol: "XAUUSD",
    direction: "buy",
    lot: 0.1,
    entry_price: 2638.1,
    close_price: 2647.3,
    sl_price: 2632.0,
    tp_price: 2648.0,
    realized_pnl: 92.0,
    status: "closed",
    opened_at: new Date(Date.now() - 180 * 60000).toISOString(),
    closed_at: new Date(Date.now() - 60 * 60000).toISOString(),
    comment: "TP hit +920 pts",
  },
];

export default function TradesPage() {
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const [trades, setTrades] = useState<Trade[]>(fallbackTrades);
  const [isLoading, setIsLoading] = useState(true);
  const [closingId, setClosingId] = useState<string | null>(null);

  const { ticks, addToast, closeTrade: wsCloseTrade } = useWebSocket();

  const loadTrades = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.trades.list({
        status: filter === "all" ? undefined : filter,
        per_page: 50,
      });
      if (res && res.trades && res.trades.length > 0) {
        setTrades(res.trades);
      }
    } catch {
      // Use fallback
    } finally {
      setIsLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadTrades();
    const interval = setInterval(loadTrades, 10000);
    return () => clearInterval(interval);
  }, [loadTrades]);

  const handleClose = async (id: string, ticket?: number | null) => {
    setClosingId(id);
    try {
      wsCloseTrade(id);
      if (id.startsWith("demo-")) {
        setTrades((prev) =>
          prev.map((t) =>
            t.id === id
              ? {
                  ...t,
                  status: "closed",
                  close_price: t.entry_price ?? t.open_price,
                  closed_at: new Date().toISOString(),
                }
              : t
          )
        );
      } else {
        await api.trades.close(id);
        await loadTrades();
      }
      addToast({
        title: "Close Order Dispatched",
        message: `Closing order for #${ticket || id.slice(0, 8)}`,
        type: "info",
      });
    } catch {
      addToast({
        title: "Close Failed",
        message: "Failed to dispatch position close command",
        type: "danger",
      });
    } finally {
      setClosingId(null);
    }
  };

  const filteredTrades = trades.filter((t) => {
    const s = (t.status || "").toLowerCase();
    if (filter === "open") return s === "open";
    if (filter === "closed") return s === "closed";
    return true;
  });

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.titleArea}>
          <h1>Trading History & Positions</h1>
          <p>Monitor live MT5 orders, executed webhooks, and historical performance</p>
        </div>

        <div className={styles.filterBar}>
          {(["all", "open", "closed"] as const).map((mode) => (
            <button
              key={mode}
              className={`${styles.filterBtn} ${
                filter === mode ? styles.filterActive : ""
              }`}
              onClick={() => setFilter(mode)}
            >
              {mode.toUpperCase()} ({trades.filter((t) => mode === "all" || (t.status || "").toLowerCase() === mode).length})
            </button>
          ))}
        </div>
      </div>

      {/* Trades Table */}
      <div className={`card ${styles.tradesTableCard}`}>
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Time</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Lots</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>SL / TP</th>
                <th>P&L</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan={11} className={styles.emptyState}>
                    No {filter} trades found.
                  </td>
                </tr>
              ) : (
                filteredTrades.map((trade) => {
                  const isBuy = (trade.direction || "").toLowerCase() === "buy";
                  const isOpen = (trade.status || "").toLowerCase() === "open";
                  const entry = trade.entry_price ?? trade.open_price ?? 0;
                  const exit = trade.close_price;
                  const sym = (trade.symbol || "").toUpperCase();
                  const tick = ticks[sym];

                  let pnl = trade.realized_pnl ?? trade.pnl ?? 0.0;
                  if (isOpen && tick && entry > 0) {
                    const currentPrice = isBuy ? tick.bid : tick.ask;
                    const mult = sym === "XAUUSD" ? 100 : 100000;
                    const lot = trade.lot_size ?? trade.lot ?? 0.1;
                    const diff = isBuy ? currentPrice - entry : entry - currentPrice;
                    pnl = Math.round(diff * lot * mult * 100) / 100;
                  }

                  const timeStr = trade.opened_at
                    ? new Date(trade.opened_at).toLocaleTimeString("en-GB", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—";

                  return (
                    <tr key={trade.id}>
                      <td className="mono" style={{ color: "var(--accent-blue)" }}>
                        #{trade.mt5_ticket || trade.id.slice(0, 8)}
                      </td>
                      <td className="mono text-muted">{timeStr}</td>
                      <td>
                        <strong>{trade.symbol}</strong>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isBuy ? "badge-success" : "badge-danger"
                          }`}
                        >
                          {trade.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="mono">{trade.lot_size ?? trade.lot ?? 0.1}</td>
                      <td className="mono">${entry.toFixed(2)}</td>
                      <td className="mono">
                        {exit ? `$${exit.toFixed(2)}` : isOpen ? (
                          <span className="text-muted">Live</span>
                        ) : "—"}
                      </td>
                      <td className="mono text-muted" style={{ fontSize: "var(--text-xs)" }}>
                        {trade.sl_price || trade.stop_loss ? `${trade.sl_price || trade.stop_loss}` : "—"} /{" "}
                        {trade.tp_price || trade.take_profit ? `${trade.tp_price || trade.take_profit}` : "—"}
                      </td>
                      <td
                        className={`mono ${
                          pnl >= 0 ? "profit" : "loss"
                        }`}
                        style={{ fontWeight: 600 }}
                      >
                        {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isOpen
                              ? "badge-info"
                              : (trade.status || "").toLowerCase() === "closed"
                              ? "badge-secondary"
                              : "badge-danger"
                          }`}
                        >
                          {trade.status.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {isOpen ? (
                          <button
                            className="btn btn-danger btn-sm"
                            disabled={closingId === trade.id}
                            onClick={() => handleClose(trade.id, trade.mt5_ticket)}
                          >
                            {closingId === trade.id ? "Closing..." : "Close"}
                          </button>
                        ) : (
                          <span className="text-muted" style={{ fontSize: "var(--text-xs)" }}>
                            Settled
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
