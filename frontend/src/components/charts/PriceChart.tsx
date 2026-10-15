"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";
import { useWebSocket } from "@/context/WebSocketContext";
import { api } from "@/lib/api";
import styles from "./PriceChart.module.css";

export default function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const lastCandleRef = useRef<any>(null);

  const [activeSymbol, setActiveSymbol] = useState("XAUUSD");
  const [activeTf, setActiveTf] = useState("1H");
  const { ticks, isConnected } = useWebSocket();

  // Load chart & candles
  useEffect(() => {
    if (!containerRef.current) return;

    // Reset old chart if exists
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
        fontFamily: "'Inter', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(30, 41, 59, 0.5)" },
        horzLines: { color: "rgba(30, 41, 59, 0.5)" },
      },
      crosshair: {
        vertLine: {
          color: "rgba(59, 130, 246, 0.3)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#3b82f6",
        },
        horzLine: {
          color: "rgba(59, 130, 246, 0.3)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#3b82f6",
        },
      },
      rightPriceScale: {
        borderColor: "#1e293b",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "#1e293b",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    candleSeriesRef.current = candleSeries;
    chartRef.current = chart;

    // Load real/fallback candles from backend
    api.trades
      .getCandles(activeSymbol)
      .then((res) => {
        if (res && res.candles && res.candles.length > 0) {
          candleSeries.setData(res.candles);
          lastCandleRef.current = { ...res.candles[res.candles.length - 1] };
          chart.timeScale().fitContent();
        }
      })
      .catch(() => null);

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [activeSymbol]);

  // Update candlestick when live tick arrives with BAR ROLLOVER
  useEffect(() => {
    const tick = ticks[activeSymbol];
    if (!tick || !candleSeriesRef.current) return;

    const currentPrice = tick.bid;
    const nowSec = Math.floor(Date.now() / 1000);
    // 1H interval = 3600s
    const barTime = nowSec - (nowSec % 3600);

    if (lastCandleRef.current) {
      const last = lastCandleRef.current;
      // If time moved to the next hour -> create new bar rollover!
      if (barTime > last.time) {
        const newBar = {
          time: barTime as any,
          open: currentPrice,
          high: currentPrice,
          low: currentPrice,
          close: currentPrice,
        };
        lastCandleRef.current = newBar;
        try {
          candleSeriesRef.current.update(newBar);
        } catch {
          // Ignore
        }
      } else {
        // Update current running bar
        const updated = {
          ...last,
          close: currentPrice,
          high: Math.max(last.high, currentPrice),
          low: Math.min(last.low, currentPrice),
        };
        lastCandleRef.current = updated;
        try {
          candleSeriesRef.current.update(updated);
        } catch {
          // Ignore
        }
      }
    } else {
      const initial = {
        time: barTime as any,
        open: currentPrice,
        high: Math.max(currentPrice, tick.ask),
        low: currentPrice,
        close: currentPrice,
      };
      lastCandleRef.current = initial;
      try {
        candleSeriesRef.current.setData([initial]);
      } catch {
        // Ignore
      }
    }
  }, [ticks, activeSymbol]);

  return (
    <div className={`card ${styles.chartCard}`}>
      <div className="card-header" style={{ flexWrap: "wrap", gap: "10px" }}>
        <div className={styles.chartHeader} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {/* Symbol Selector */}
          <select
            value={activeSymbol}
            onChange={(e) => setActiveSymbol(e.target.value)}
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-primary)",
              color: "var(--text-primary)",
              fontWeight: 700,
              fontSize: "var(--text-sm)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              cursor: "pointer",
            }}
          >
            <option value="XAUUSD">XAUUSD • Gold</option>
            <option value="EURUSD">EURUSD</option>
            <option value="GBPUSD">GBPUSD</option>
            <option value="BTCUSD">BTCUSD</option>
          </select>

          <div className={styles.chartBadges}>
            <span className="badge badge-info">Real-Time</span>
            <span
              className={`badge ${
                isConnected ? "badge-success" : "badge-secondary"
              }`}
            >
              <span
                className={`pulse-dot ${
                  isConnected ? "pulse-dot-green" : "pulse-dot-amber"
                }`}
                style={{ width: 6, height: 6 }}
              />
              {isConnected ? "Live Streaming" : "Waiting Feed"}
            </span>
          </div>
        </div>

        <div className={styles.timeframes}>
          {["15m", "1H", "4H", "1D"].map((tf) => (
            <button
              key={tf}
              onClick={() => setActiveTf(tf)}
              className={`${styles.tfBtn} ${activeTf === tf ? styles.tfActive : ""}`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div ref={containerRef} className={styles.chartContainer} />
    </div>
  );
}
