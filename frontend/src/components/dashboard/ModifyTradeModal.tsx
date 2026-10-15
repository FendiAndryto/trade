"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Trade } from "@/lib/types";

interface ModifyTradeModalProps {
  trade: Trade | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ModifyTradeModal({
  trade,
  isOpen,
  onClose,
  onSuccess,
}: ModifyTradeModalProps) {
  const [sl, setSl] = useState(trade?.stop_loss ? String(trade.stop_loss) : "");
  const [tp, setTp] = useState(trade?.take_profit ? String(trade.take_profit) : "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !trade) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await api.trades.modify(trade.id, {
        stop_loss: sl ? parseFloat(sl) : undefined,
        take_profit: tp ? parseFloat(tp) : undefined,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal mengubah posisi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.7)",
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
          maxWidth: "400px",
          width: "100%",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-primary)",
        }}
      >
        <div className="card-header">
          <div>
            <span className="card-title">Modifikasi SL / TP</span>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", display: "block" }}>
              #{trade.mt5_ticket || trade.id.slice(0, 8)} • {trade.symbol} (
              {trade.direction.toUpperCase()})
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
              padding: "10px",
              borderRadius: "var(--radius-md)",
              fontSize: "var(--text-xs)",
              marginBottom: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}>
          <div>
            <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
              Stop Loss (SL)
            </label>
            <input
              type="number"
              step="any"
              placeholder="Kosongkan jika tanpa SL"
              value={sl}
              onChange={(e) => setSl(e.target.value)}
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
              placeholder="Kosongkan jika tanpa TP"
              value={tp}
              onChange={(e) => setTp(e.target.value)}
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

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Batal
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
