"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Trade } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./ActiveTrades.module.css";

const fallbackTrades: Trade[] = [
  {
    id: "demo-1",
    symbol: "XAUUSD",
    direction: "buy",
    lot: 0.15,
    open_price: 2648.5,
    sl_price: 2642.0,
    tp_price: 2665.0,
    pnl: 192.0,
    status: "open",
    opened_at: new Date(Date.now() - 42 * 60000).toISOString(),
    comment: "Trend pullback entry",
  },
  {
    id: "demo-2",
    symbol: "EURUSD",
    direction: "sell",
    lot: 0.2,
    open_price: 1.0892,
    sl_price: 1.0915,
    tp_price: 1.084,
    pnl: 37.0,
    status: "open",
    opened_at: new Date(Date.now() - 15 * 60000).toISOString(),
    comment: "Bearish pin bar",
  },
];

export default function ActiveTrades() {
  const [trades, setTrades] = useState<Trade[]>(fallbackTrades);
  const [closingId, setClosingId] = useState<string | null>(null);
  const { closeTrade, ticks } = useWebSocket();

  const fetchTrades = useCallback(async () => {
    try {
      const res = await api.trades.list({ status: "open" });
      if (res && res.trades && res.trades.length > 0) {
        setTrades(res.trades);
      }
    } catch {
      // Keep fallback trades
    }
  }, []);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 10000);
    return () => clearInterval(interval);
  }, [fetchTrades]);

  const handleCloseTrade = async (id: string) => {
    setClosingId(id);
    try {
      closeTrade(id);
      if (id.startsWith("demo-")) {
        // Instant simulated close
        setTrades((prev) => prev.filter((t) => t.id !== id));
      } else {
        await api.trades.close(id);
        await fetchTrades();
      }
    } catch {
      setTrades((prev) => prev.filter((t) => t.id !== id));
    } finally {
      setClosingId(null);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Active Positions</span>
        <span className="badge badge-info">{trades.length} Open</span>
      </div>

      <div className={styles.tradesList}>
        {trades.map((trade) => {
          const entry = trade.open_price ?? trade.entry_price ?? 0;
          const sl = trade.sl_price ?? trade.stop_loss;
          const tp = trade.tp_price ?? trade.take_profit;
          const isBuy = trade.direction.toLowerCase() === "buy";
          const sym = trade.symbol.toUpperCase();
          const tick = ticks[sym];

          let pnl = trade.pnl ?? trade.realized_pnl ?? 0.0;
          if (tick && entry > 0) {
            const currentPrice = isBuy ? tick.bid : tick.ask;
            const mult = sym === "XAUUSD" ? 100 : 100000;
            const lot = trade.lot ?? trade.lot_size ?? 0.1;
            const diff = isBuy ? currentPrice - entry : entry - currentPrice;
            pnl = Math.round(diff * lot * mult * 100) / 100;
          }

          return (
            <div key={trade.id} className={styles.tradeRow}>
              <div className={styles.tradeInfo}>
                <div className={styles.tradeSymbol}>
                  <span
                    className={`badge ${
                      isBuy ? "badge-success" : "badge-danger"
                    }`}
                  >
                    {trade.direction.toUpperCase()}
                  </span>
                  <span className={styles.symbol}>{trade.symbol}</span>
                  <span className="text-muted">{trade.lot ?? trade.lot_size} lots</span>
                </div>
                <div className={styles.tradePrices}>
                  <span className="text-muted">
                    Entry: <span className="mono">{entry.toFixed(trade.symbol.includes("USD") && !trade.symbol.includes("XAU") ? 5 : 2)}</span>
                  </span>
                  {sl && (
                    <>
                      <span className="text-muted">•</span>
                      <span className="text-muted">
                        SL: <span className="mono">{sl}</span>
                      </span>
                    </>
                  )}
                  {tp && (
                    <>
                      <span className="text-muted">•</span>
                      <span className="text-muted">
                        TP: <span className="mono">{tp}</span>
                      </span>
                    </>
                  )}
                </div>
              </div>
              <div className={styles.tradeRight}>
                <div
                  className={`${styles.tradePnl} mono ${
                    pnl >= 0 ? "profit" : "loss"
                  }`}
                  style={{ transition: "color 0.2s ease" }}
                >
                  {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                </div>
                <div className={styles.tradeActions}>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={closingId === trade.id}
                    onClick={() => handleCloseTrade(trade.id)}
                  >
                    {closingId === trade.id ? "Closing..." : "Close Position"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {trades.length === 0 && (
          <div className={styles.emptyState}>
            <span className="text-muted">No open positions currently</span>
          </div>
        )}
      </div>
    </div>
  );
}
