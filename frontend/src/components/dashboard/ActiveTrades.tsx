"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Trade } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import QuickOrderModal from "./QuickOrderModal";
import ModifyTradeModal from "./ModifyTradeModal";
import styles from "./ActiveTrades.module.css";

export default function ActiveTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [closingId, setClosingId] = useState<string | null>(null);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [modifyingTrade, setModifyingTrade] = useState<Trade | null>(null);

  const { closeTrade, ticks } = useWebSocket();

  const fetchTrades = useCallback(async () => {
    try {
      const res = await api.trades.list({ status: "open" });
      setTrades(res?.trades || []);
    } catch {
      // Ignore transient errors
    }
  }, []);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, 6000);
    return () => clearInterval(interval);
  }, [fetchTrades]);

  const handleCloseTrade = async (id: string) => {
    setClosingId(id);
    try {
      closeTrade(id);
      if (id.startsWith("demo-")) {
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
    <>
      <div className="card">
        <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span className="card-title">Active Positions</span>
            <span className="badge badge-info">{trades.length} Open</span>
          </div>
          <button
            className="btn btn-primary btn-sm"
            style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}
            onClick={() => setIsOrderModalOpen(true)}
          >
            <span>⚡</span> + New Order / Entry
          </button>
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
                    {sl ? (
                      <>
                        <span className="text-muted">•</span>
                        <span className="text-muted">
                          SL: <span className="mono">{sl}</span>
                        </span>
                      </>
                    ) : null}
                    {tp ? (
                      <>
                        <span className="text-muted">•</span>
                        <span className="text-muted">
                          TP: <span className="mono">{tp}</span>
                        </span>
                      </>
                    ) : null}
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
                  <div className={styles.tradeActions} style={{ display: "flex", gap: "6px" }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: "var(--text-xs)", padding: "4px 8px" }}
                      onClick={() => setModifyingTrade(trade)}
                    >
                      Edit SL/TP
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={closingId === trade.id}
                      onClick={() => handleCloseTrade(trade.id)}
                    >
                      {closingId === trade.id ? "Closing..." : "Close"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {trades.length === 0 && (
            <div className={styles.emptyState}>
              <span className="text-muted">Tidak ada posisi terbuka saat ini.</span>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <QuickOrderModal
        isOpen={isOrderModalOpen}
        onClose={() => setIsOrderModalOpen(false)}
        onOrderSuccess={fetchTrades}
      />

      <ModifyTradeModal
        trade={modifyingTrade}
        isOpen={!!modifyingTrade}
        onClose={() => setModifyingTrade(null)}
        onSuccess={fetchTrades}
      />
    </>
  );
}
