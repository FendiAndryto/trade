"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/context/WebSocketContext";

interface QuickOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOrderSuccess: () => void;
}

export default function QuickOrderModal({
  isOpen,
  onClose,
  onOrderSuccess,
}: QuickOrderModalProps) {
  const [symbol, setSymbol] = useState("XAUUSD");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [lotSize, setLotSize] = useState("0.01");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { ticks } = useWebSocket();
  const currentTick = ticks[symbol];

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const lot = parseFloat(lotSize);
      if (isNaN(lot) || lot <= 0) {
        setErrorMsg("Ukuran lot tidak valid.");
        setIsSubmitting(false);
        return;
      }

      await api.trades.createManual({
        symbol: symbol.toUpperCase(),
        direction,
        lot_size: lot,
        stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
        take_profit: takeProfit ? parseFloat(takeProfit) : undefined,
        comment: `Web: ${direction.toUpperCase()} ${symbol}`,
      });

      onOrderSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal mengeksekusi order. Coba lagi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentPrice = currentTick
    ? direction === "buy"
      ? currentTick.ask
      : currentTick.bid
    : null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10000,
        padding: "20px",
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: "440px",
          width: "100%",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-primary)",
          boxShadow: "0 12px 32px rgba(0,0,0,0.5)",
        }}
      >
        <div className="card-header" style={{ marginBottom: "16px" }}>
          <div>
            <span className="card-title">Quick Manual Entry</span>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", display: "block" }}>
              Eksekusi order langsung ke MT5 terminal
            </span>
          </div>
          <button
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              fontSize: "18px",
              cursor: "pointer",
            }}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid #ef4444",
              color: "#f87171",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              fontSize: "var(--text-xs)",
              marginBottom: "14px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {/* Symbol & Direction Toggle */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Pilih Simbol
              </label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-primary)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "var(--text-sm)",
                  fontWeight: 600,
                }}
              >
                <option value="XAUUSD">XAUUSD (Gold)</option>
                <option value="EURUSD">EURUSD</option>
                <option value="GBPUSD">GBPUSD</option>
                <option value="BTCUSD">BTCUSD</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Arah Posisi
              </label>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  type="button"
                  onClick={() => setDirection("buy")}
                  style={{
                    flex: 1,
                    padding: "9px 0",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    background: direction === "buy" ? "#10b981" : "var(--bg-secondary)",
                    color: direction === "buy" ? "#fff" : "var(--text-muted)",
                    fontWeight: 700,
                    fontSize: "var(--text-xs)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setDirection("sell")}
                  style={{
                    flex: 1,
                    padding: "9px 0",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    background: direction === "sell" ? "#ef4444" : "var(--bg-secondary)",
                    color: direction === "sell" ? "#fff" : "var(--text-muted)",
                    fontWeight: 700,
                    fontSize: "var(--text-xs)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  SELL
                </button>
              </div>
            </div>
          </div>

          {/* Running Price Preview */}
          <div
            style={{
              padding: "10px 14px",
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "var(--text-xs)",
            }}
          >
            <span className="text-muted">Harga Pasar Saat Ini:</span>
            <span className="mono" style={{ fontWeight: 700, color: direction === "buy" ? "#34d399" : "#f87171" }}>
              {currentPrice ? currentPrice.toFixed(symbol === "XAUUSD" ? 2 : 5) : "Menunggu tick..."}
            </span>
          </div>

          {/* Lot Size */}
          <div>
            <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
              Ukuran Lot (Volume) *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="10.0"
              value={lotSize}
              onChange={(e) => setLotSize(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-primary)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
              }}
            />
          </div>

          {/* Stop Loss & Take Profit */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Stop Loss (SL)
              </label>
              <input
                type="number"
                step="any"
                placeholder="Opsional"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-primary)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontFamily: "var(--font-mono)",
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Take Profit (TP)
              </label>
              <input
                type="number"
                step="any"
                placeholder="Opsional"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-primary)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontFamily: "var(--font-mono)",
                }}
              />
            </div>
          </div>

          {/* Submit Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Batal
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: "10px 20px",
                borderRadius: "var(--radius-md)",
                border: "none",
                fontWeight: 700,
                fontSize: "var(--text-sm)",
                color: "#fff",
                cursor: "pointer",
                background: direction === "buy" ? "#10b981" : "#ef4444",
                boxShadow:
                  direction === "buy"
                    ? "0 4px 14px rgba(16, 185, 129, 0.4)"
                    : "0 4px 14px rgba(239, 68, 68, 0.4)",
              }}
            >
              {isSubmitting
                ? "Mengeksekusi..."
                : `Eksekusi ${direction.toUpperCase()} ${lotSize} Lot`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
