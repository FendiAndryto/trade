"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import StatCards from "@/components/dashboard/StatCards";
import ActiveTrades from "@/components/dashboard/ActiveTrades";
import RecentWebhooks from "@/components/dashboard/RecentWebhooks";
import RiskMeter from "@/components/dashboard/RiskMeter";

// Lazy load charts (uses window/document)
const PriceChart = dynamic(() => import("@/components/charts/PriceChart"), {
  ssr: false,
  loading: () => (
    <div className="card" style={{ height: 490 }}>
      <div className="skeleton" style={{ width: "100%", height: "100%" }} />
    </div>
  ),
});

const EquityCurveChart = dynamic(
  () => import("@/components/charts/EquityCurveChart"),
  {
    ssr: false,
    loading: () => (
      <div className="card" style={{ height: 490 }}>
        <div className="skeleton" style={{ width: "100%", height: "100%" }} />
      </div>
    ),
  }
);

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"price" | "equity">("price");

  return (
    <>
      {/* Stat Cards Row */}
      <StatCards />

      {/* Main Grid: Chart + Sidebar */}
      <div className="dashboard-grid">
        <div className="dashboard-main">
          {/* Chart View Switcher */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "-8px",
            }}
          >
            <div
              style={{
                display: "inline-flex",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                padding: "3px",
                gap: "4px",
                border: "1px solid var(--border-primary)",
              }}
            >
              <button
                onClick={() => setActiveTab("price")}
                style={{
                  background:
                    activeTab === "price"
                      ? "var(--bg-elevated)"
                      : "transparent",
                  color:
                    activeTab === "price"
                      ? "var(--text-primary)"
                      : "var(--text-muted)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 14px",
                  fontSize: "var(--text-xs)",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  boxShadow:
                    activeTab === "price"
                      ? "0 2px 8px rgba(0,0,0,0.25)"
                      : "none",
                  transition: "all 0.15s ease",
                }}
              >
                <span>📈</span> Live Candlesticks
              </button>
              <button
                onClick={() => setActiveTab("equity")}
                style={{
                  background:
                    activeTab === "equity"
                      ? "var(--bg-elevated)"
                      : "transparent",
                  color:
                    activeTab === "equity"
                      ? "var(--text-primary)"
                      : "var(--text-muted)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  padding: "6px 14px",
                  fontSize: "var(--text-xs)",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  boxShadow:
                    activeTab === "equity"
                      ? "0 2px 8px rgba(0,0,0,0.25)"
                      : "none",
                  transition: "all 0.15s ease",
                }}
              >
                <span>📊</span> Equity Growth Curve
              </button>
            </div>
          </div>

          {activeTab === "price" ? <PriceChart /> : <EquityCurveChart />}

          <ActiveTrades />
        </div>
        <div className="dashboard-side">
          <RiskMeter />
          <RecentWebhooks />
        </div>
      </div>
    </>
  );
}

