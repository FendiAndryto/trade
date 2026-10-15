"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

interface MT5AccountItem {
  id: string;
  mt5_login: number;
  server_name: string;
  broker_name: string;
  status: string;
  balance: number;
  equity: number;
  pairing_code?: string;
  last_sync_at?: string;
}

export default function AccountsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [accounts, setAccounts] = useState<MT5AccountItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Form states
  const [formLogin, setFormLogin] = useState("");
  const [formServer, setFormServer] = useState("Exness-Real10");
  const [formBroker, setFormBroker] = useState("Exness");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { isConnected, accountUpdate } = useWebSocket();

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [sumRes, accRes] = await Promise.all([
        api.dashboard.getSummary().catch(() => null),
        api.accounts.list().catch(() => []),
      ]);
      if (sumRes) setSummary(sumRes);
      if (Array.isArray(accRes)) setAccounts(accRes);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formLogin || !formServer) {
      showToast("Harap isi Nomor Akun dan Server Broker.");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await api.accounts.create({
        mt5_login: parseInt(formLogin.trim(), 10),
        server_name: formServer.trim(),
        broker_name: formBroker.trim(),
      });
      setAccounts((prev) => [created, ...prev]);
      setShowModal(false);
      setFormLogin("");
      showToast(`Akun #${created.mt5_login} berhasil ditambahkan! Pasang EA dengan kode pairing.`);
    } catch {
      showToast("Gagal menambahkan akun. Coba lagi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAccount = async (id: string, loginNum: number) => {
    if (!confirm(`Hapus koneksi akun MT5 #${loginNum}?`)) return;
    try {
      await api.accounts.delete(id);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
      showToast(`Akun #${loginNum} telah dihapus.`);
    } catch {
      showToast("Gagal menghapus akun.");
    }
  };

  const copyPairingCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    showToast(`Kode Pairing ${code} disalin ke clipboard!`);
    setTimeout(() => setCopiedCode(null), 3000);
  };

  const handleDownloadEa = (pairingCode: string = "") => {
    const apiUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/api/v1`
        : "https://trade.homever.my.id/api/v1";
    const downloadUrl = `${apiUrl}/accounts/download-ea?pairing_code=${encodeURIComponent(
      pairingCode
    )}`;
    window.open(downloadUrl, "_blank");
    showToast("Mengunduh Expert Advisor TradeGearBridge.mq5...");
  };

  // Primary active account info (live from WS or fallback to summary)
  const primaryAccount = accounts[0];
  const balance =
    accountUpdate?.balance ?? primaryAccount?.balance ?? summary?.account.balance ?? 0;
  const equity =
    accountUpdate?.equity ?? primaryAccount?.equity ?? summary?.account.equity ?? 0;
  const floatingPnl = equity > 0 && balance > 0 ? equity - balance : 0;
  const activeLogin = accountUpdate?.login ?? primaryAccount?.mt5_login ?? summary?.account.login;
  const activeServer =
    accountUpdate?.server ?? primaryAccount?.server_name ?? summary?.account.server;
  const activeBroker =
    accountUpdate?.company ?? primaryAccount?.broker_name ?? summary?.account.broker;

  const serverDomain =
    typeof window !== "undefined" ? window.location.origin : "https://trade.homever.my.id";

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Toast Alert */}
      {toastMsg && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--accent-primary)",
            color: "var(--text-primary)",
            padding: "12px 20px",
            borderRadius: "var(--radius-md)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
            zIndex: 9999,
            fontSize: "var(--text-sm)",
            fontWeight: 500,
          }}
        >
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div
        className={styles.pageHeader}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <h1>MetaTrader 5 No-Code Bridge</h1>
          <p>
            Hubungkan terminal MT5 Anda langsung dari website tanpa perlu coding atau buka terminal.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => handleDownloadEa(primaryAccount?.pairing_code || "")}
          >
            📥 Download EA (.mq5)
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowModal(true)}
          >
            + Hubungkan Akun MT5 Baru
          </button>
        </div>
      </div>

      <div className={styles.accountsGrid}>
        {/* Left Column: Live Terminal Status Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Live Terminal Status</span>
            <span
              className={`badge ${
                isConnected ? "badge-success" : "badge-secondary"
              }`}
            >
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
                {activeLogin ? `#${activeLogin}` : "Belum Ada Akun Terhubung"}
              </span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Broker Server</span>
              <span>{activeServer || "—"}</span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Broker Name</span>
              <span>{activeBroker || "—"}</span>
            </div>
            <div className={styles.detailRow}>
              <span className="text-muted">Balance</span>
              <span className="mono">
                ${balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
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
              <span className="text-muted">Protokol Sinkronisasi</span>
              <span className="badge badge-info">OnTradeTransaction Real-time</span>
            </div>
          </div>

          {/* Quick Connection Info */}
          {primaryAccount && (
            <div
              style={{
                marginTop: "20px",
                padding: "16px",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                border: "1px dashed var(--border-primary)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                    Kode Pairing Akun Ini:
                  </div>
                  <div
                    className="mono"
                    style={{
                      fontSize: "var(--text-lg)",
                      fontWeight: 700,
                      color: "var(--accent-primary)",
                      letterSpacing: "1px",
                    }}
                  >
                    {primaryAccount.pairing_code || "TG-884920"}
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => copyPairingCode(primaryAccount.pairing_code || "TG-884920")}
                >
                  {copiedCode === primaryAccount.pairing_code ? "✓ Disalin" : "Salin Kode"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: 3-Step No-Code Setup Guide */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Cara Pasang di MT5 (3 Langkah Cepat)</span>
            <span className="badge badge-info">100% No-Code</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}>
            <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "var(--accent-primary)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "14px",
                  flexShrink: 0,
                }}
              >
                1
              </div>
              <div>
                <strong style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
                  Download EA TradeGearBridge
                </strong>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Klik tombol download di atas untuk mengunduh file <code>TradeGearBridge.mq5</code>.
                </p>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "var(--accent-primary)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "14px",
                  flexShrink: 0,
                }}
              >
                2
              </div>
              <div>
                <strong style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
                  Pasang di Chart MetaTrader 5
                </strong>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Di MT5, buka menu <code>File → Open Data Folder → MQL5 → Experts</code>, lalu paste file EA di sana. Buka Navigator (Ctrl+N), klik kanan Expert Advisors → Refresh, lalu drag EA ke salah satu chart (misal XAUUSD).
                </p>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "var(--accent-primary)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "14px",
                  flexShrink: 0,
                }}
              >
                3
              </div>
              <div>
                <strong style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
                  Masukkan Kode Pairing & Izinkan WebRequest
                </strong>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Di tab Inputs EA, masukkan <strong>Kode Pairing</strong> Anda. Pastikan di MT5 (<code>Tools → Options → Expert Advisors</code>) centang <strong>"Allow WebRequest for listed URL"</strong> dan tambahkan URL:
                </p>
                <div
                  className="mono"
                  style={{
                    background: "var(--bg-elevated)",
                    padding: "6px 10px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "var(--text-xs)",
                    color: "var(--text-primary)",
                    marginTop: "6px",
                  }}
                >
                  {serverDomain}
                </div>
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: "20px",
              padding: "12px",
              background: "rgba(16, 185, 129, 0.1)",
              borderRadius: "var(--radius-md)",
              border: "1px solid rgba(16, 185, 129, 0.2)",
              fontSize: "var(--text-xs)",
              color: "#34d399",
            }}
          >
            ✓ Begitu Anda klik <strong>OK</strong> di MT5, akun Anda akan otomatis terhubung secara live ke website ini!
          </div>
        </div>
      </div>

      {/* Modal: Tambah Akun MT5 Baru */}
      {showModal && (
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
              maxWidth: "480px",
              width: "100%",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-primary)",
            }}
          >
            <div className="card-header">
              <span className="card-title">Hubungkan Akun MT5 Baru</span>
              <button
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  fontSize: "18px",
                  cursor: "pointer",
                }}
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAccount} style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}>
              <div>
                <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Nomor Akun MT5 (Login ID) *
                </label>
                <input
                  type="number"
                  placeholder="Contoh: 10928374"
                  value={formLogin}
                  onChange={(e) => setFormLogin(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-primary)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "var(--text-sm)",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Server Broker *
                </label>
                <input
                  type="text"
                  placeholder="Contoh: Exness-Real10 atau ICMarkets-Live"
                  value={formServer}
                  onChange={(e) => setFormServer(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-primary)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "var(--text-sm)",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Nama Broker (Opsional)
                </label>
                <input
                  type="text"
                  placeholder="Contoh: Exness / ICMarkets / MetaQuotes"
                  value={formBroker}
                  onChange={(e) => setFormBroker(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-primary)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "var(--text-sm)",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Memproses..." : "Dapatkan Kode Pairing"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
