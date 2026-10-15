"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";
import { useWebSocket } from "@/context/WebSocketContext";
import styles from "./PriceChart.module.css";

// Generate mock XAUUSD candlestick data
function generateMockCandles() {
  const data = [];
  let time = new Date("2024-09-01").getTime() / 1000;
  let open = 2500;

  for (let i = 0; i < 120; i++) {
    const close = open + (Math.random() - 0.48) * 15;
    const high = Math.max(open, close) + Math.random() * 10;
    const low = Math.min(open, close) - Math.random() * 10;

    data.push({
      time: time as any,
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
    });

    time += 3600; // 1 hour candles
    open = close;
  }
  return data;
}

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

    const data = generateMockCandles();
    candleSeries.setData(data);
    candleSeriesRef.current = candleSeries;
    lastCandleRef.current = { ...data[data.length - 1] };

    // Add entry line marker
    const lastPrice = data[data.length - 1].close;
    candleSeries.createPriceLine({
      price: lastPrice - 20,
      color: "#3b82f6",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "Entry",
    });
    candleSeries.createPriceLine({
      price: lastPrice - 50,
      color: "#ef4444",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "SL",
    });
    candleSeries.createPriceLine({
      price: lastPrice + 30,
      color: "#10b981",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "TP",
    });

    chart.timeScale().fitContent();
    chartRef.current = chart;

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
    if (!tick || !candleSeriesRef.current || !lastCandleRef.current) return;

    const last = lastCandleRef.current;
    const currentPrice = tick.bid;
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
