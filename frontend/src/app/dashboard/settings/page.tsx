"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./page.module.css";

export default function SettingsPage() {
  const { user } = useAuth();
  const { addToast } = useWebSocket();

  const [copiedField, setCopiedField] = useState<string | null>(null);

  const serverUrl =
    typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname}:8001`
      : "http://localhost:8001";

  const sampleToken = "tg_live_79a2b8e3c4d5f6a1b2c3d4e5f6a7b8c9";

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    addToast({
      title: "Copied to Clipboard",
      message: `${label} copied.`,
      type: "success",
    });
    setTimeout(() => setCopiedField(null), 2500);
  };

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <h1>Account & Integration Settings</h1>
        <p>Manage your TradingView webhook endpoints, API tokens, and account profile</p>
      </div>

      <div className={styles.settingsGrid}>
        {/* User Profile */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">User Profile</span>
            <span className="badge badge-info">{user?.plan?.toUpperCase() || "PRO TIER"}</span>
          </div>

          <div className={styles.fieldGroup}>
            <label>Display Name</label>
            <input
              type="text"
              className="input"
              value={user?.display_name || "Pro Trader"}
              readOnly
            />
          </div>

          <div className={styles.fieldGroup}>
            <label>Email Address</label>
            <input
              type="text"
              className="input"
              value={user?.email || "trader@example.com"}
              readOnly
            />
          </div>
        </div>

        {/* Webhook API Authentication */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">TradingView Webhook Integration</span>
            <span className="badge badge-success">Active Token</span>
          </div>

          <div className={styles.fieldGroup}>
            <label>Backend Server Host</label>
            <div className={styles.copyInputGroup}>
              <input type="text" className="input mono" value={serverUrl} readOnly />
              <button
                className="btn btn-secondary"
                onClick={() => handleCopy(serverUrl, "Server Host")}
              >
                {copiedField === "Server Host" ? "✓" : "Copy"}
              </button>
            </div>
            <span className={styles.helperText}>
              Ensure port 8001 is publicly reachable if using remote TradingView webhooks.
            </span>
          </div>

          <div className={styles.fieldGroup}>
            <label>Global Webhook Bearer Token</label>
            <div className={styles.copyInputGroup}>
              <input type="text" className="input mono" value={sampleToken} readOnly />
              <button
                className="btn btn-secondary"
                onClick={() => handleCopy(sampleToken, "Webhook Token")}
              >
                {copiedField === "Webhook Token" ? "✓" : "Copy"}
              </button>
            </div>
            <span className={styles.helperText}>
              Include in TradingView Webhook URL query: <code>?token={sampleToken}</code>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
