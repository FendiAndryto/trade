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

  const { ticks, isConnected } = useWebSocket();

  useEffect(() => {
    if (!containerRef.current) return;

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

    // Load real candles from MetaTrader 5 via backend
    api.trades.getCandles("XAUUSD")
      .then((res) => {
        if (res && res.candles && res.candles.length > 0) {
          candleSeries.setData(res.candles);
          lastCandleRef.current = { ...res.candles[res.candles.length - 1] };
          chart.timeScale().fitContent();
        }
      })
      .catch(() => null);

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({
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
    };
  }, []);

  // Update candlestick when live tick arrives
  useEffect(() => {
    const tick = ticks["XAUUSD"];
    if (!tick || !candleSeriesRef.current) return;

    const currentPrice = tick.bid;
    if (lastCandleRef.current) {
      const last = lastCandleRef.current;
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
        // Ignore transient errors
      }
    } else {
      const nowSec = Math.floor(Date.now() / 1000);
      const hourSec = nowSec - (nowSec % 3600);
      const initial = {
        time: hourSec as any,
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
  }, [ticks]);

  return (
    <div className={`card ${styles.chartCard}`}>
      <div className="card-header">
        <div className={styles.chartHeader}>
          <span className="card-title">XAUUSD • 1H</span>
          <div className={styles.chartBadges}>
            <span className="badge badge-info">Live</span>
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
              {isConnected ? "Streaming" : "Offline"}
            </span>
          </div>
        </div>
        <div className={styles.timeframes}>
          {["5m", "15m", "1H", "4H", "1D"].map((tf) => (
            <button
              key={tf}
              className={`${styles.tfBtn} ${tf === "1H" ? styles.tfActive : ""}`}
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
