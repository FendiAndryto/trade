"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./Topbar.module.css";

export default function Topbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { isConnected, ticks } = useWebSocket();

  const userInitial = user?.display_name
    ? user.display_name.charAt(0).toUpperCase()
    : user?.email
    ? user.email.charAt(0).toUpperCase()
    : "T";

  const xauTick = ticks["XAUUSD"];
  const displayPrice = xauTick ? xauTick.bid.toFixed(2) : "2,651.30";
  const direction = xauTick?.direction || "flat";

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <h1 className={styles.pageTitle}>Dashboard</h1>
      </div>

      <div className={styles.right}>
        {/* Live price ticker */}
        <div className={styles.priceTicker}>
          <span
            className={`pulse-dot ${
              isConnected ? "pulse-dot-green" : "pulse-dot-amber"
            }`}
            style={{ width: 7, height: 7, marginRight: 2 }}
          />
          <span className={styles.tickerSymbol}>XAUUSD</span>
          <span
            className={`${styles.tickerPrice} mono ${
              direction === "up" ? "profit" : direction === "down" ? "loss" : ""
            }`}
            style={{
              transition: "color 0.2s ease, text-shadow 0.2s ease",
              textShadow:
                direction === "up"
                  ? "0 0 10px rgba(16, 185, 129, 0.4)"
                  : direction === "down"
                  ? "0 0 10px rgba(239, 68, 68, 0.4)"
                  : "none",
            }}
          >
            {displayPrice}
          </span>
          <span
            className={`${styles.tickerChange} ${
              direction === "down" ? "loss" : "profit"
            }`}
          >
            {direction === "down" ? "▼ -0.15%" : "▲ +0.42%"}
          </span>
        </div>

        {/* Separator */}
        <div className={styles.separator} />

        {/* Account quick info */}
        <div className={styles.accountInfo}>
          <div className={styles.accountBalance}>
            <span className={styles.accountLabel}>
              {user ? user.display_name || user.email : "Account"}
            </span>
            <span className={`${styles.accountValue} mono`}>
              {user?.plan === "pro" ? "PRO TIER" : "FREE TIER"}
            </span>
          </div>
        </div>

        {/* User avatar / actions */}
        {isAuthenticated ? (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              className={styles.avatar}
              title={`${user?.display_name || user?.email} (Click to logout)`}
              onClick={logout}
            >
              <span>{userInitial}</span>
            </div>
            <button
              onClick={logout}
              style={{
                background: "transparent",
                border: "1px solid var(--border-primary)",
                color: "var(--text-muted)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                fontSize: "11px",
                cursor: "pointer",
              }}
            >
              Logout
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            style={{
              background: "var(--accent-blue)",
              color: "white",
              padding: "6px 14px",
              borderRadius: "var(--radius-md)",
              fontSize: "12px",
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
