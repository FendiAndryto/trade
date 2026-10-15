"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createChart, ColorType, AreaSeries, LineSeries } from "lightweight-charts";
import { api } from "@/lib/api";
import { EquityPoint } from "@/lib/types";
import styles from "./EquityCurveChart.module.css";

const fallbackData: EquityPoint[] = [
  { date: "2026-10-02", balance: 10000.0, equity: 10035.0, pnl: 35.0 },
  { date: "2026-10-03", balance: 10035.0, equity: 10082.5, pnl: 47.5 },
  { date: "2026-10-04", balance: 10082.5, equity: 10060.0, pnl: -22.5 },
  { date: "2026-10-05", balance: 10060.0, equity: 10115.0, pnl: 55.0 },
  { date: "2026-10-06", balance: 10115.0, equity: 10140.2, pnl: 25.2 },
  { date: "2026-10-07", balance: 10140.2, equity: 10110.0, pnl: -30.2 },
  { date: "2026-10-08", balance: 10110.0, equity: 10178.4, pnl: 68.4 },
  { date: "2026-10-09", balance: 10178.4, equity: 10210.0, pnl: 31.6 },
  { date: "2026-10-10", balance: 10210.0, equity: 10185.0, pnl: -25.0 },
  { date: "2026-10-11", balance: 10185.0, equity: 10240.0, pnl: 55.0 },
  { date: "2026-10-12", balance: 10240.0, equity: 10275.5, pnl: 35.5 },
  { date: "2026-10-13", balance: 10275.5, equity: 10250.0, pnl: -25.5 },
  { date: "2026-10-14", balance: 10250.0, equity: 10300.0, pnl: 50.0 },
  { date: "2026-10-15", balance: 10300.0, equity: 10312.5, pnl: 12.5 },
];

export default function EquityCurveChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const areaSeriesRef = useRef<any>(null);
  const lineSeriesRef = useRef<any>(null);

  const [days, setDays] = useState<number>(30);
  const [dataPoints, setDataPoints] = useState<EquityPoint[]>(fallbackData);

  const loadData = useCallback(async () => {
    try {
      const res = await api.dashboard.getEquityCurve(days);
      if (res && res.data && res.data.length > 0) {
        setDataPoints(res.data);
      }
    } catch {
      // Fallback
    }
  }, [days]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
        vertLines: { color: "rgba(30, 41, 59, 0.4)" },
        horzLines: { color: "rgba(30, 41, 59, 0.4)" },
      },
      crosshair: {
        vertLine: {
          color: "rgba(16, 185, 129, 0.3)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#10b981",
        },
        horzLine: {
          color: "rgba(16, 185, 129, 0.3)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#10b981",
        },
      },
      rightPriceScale: {
        borderColor: "#1e293b",
        scaleMargins: { top: 0.15, bottom: 0.15 },
      },
      timeScale: {
        borderColor: "#1e293b",
        timeVisible: true,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(16, 185, 129, 0.35)",
      bottomColor: "rgba(16, 185, 129, 0.0)",
      lineColor: "#10b981",
      lineWidth: 2,
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    const lineSeries = chart.addSeries(LineSeries, {
      color: "rgba(148, 163, 184, 0.5)",
      lineWidth: 1,
      lineStyle: 2, // Dashed
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    chartRef.current = chart;
    areaSeriesRef.current = areaSeries;
    lineSeriesRef.current = lineSeries;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!areaSeriesRef.current || !lineSeriesRef.current || dataPoints.length === 0) return;

    const equityData = dataPoints.map((p) => ({
      time: p.date,
      value: p.equity,
    }));

    const balanceData = dataPoints.map((p) => ({
      time: p.date,
      value: p.balance,
    }));

    areaSeriesRef.current.setData(equityData);
    lineSeriesRef.current.setData(balanceData);

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [dataPoints]);

  const startingBalance = dataPoints[0]?.balance ?? 10000;
  const latestEquity = dataPoints[dataPoints.length - 1]?.equity ?? 10312.5;
  const netPnl = latestEquity - startingBalance;
  const netPnlPct = startingBalance > 0 ? (netPnl / startingBalance) * 100 : 0;
  const peakEquity = Math.max(...dataPoints.map((d) => d.equity), latestEquity);

  return (
    <div className={`card ${styles.equityCard}`}>
      <div className="card-header">
        <div className={styles.headerLeft}>
          <span className="card-title">Account Equity Curve</span>
          <span className="badge badge-success">
            {netPnl >= 0 ? "+" : ""}${netPnl.toFixed(2)} ({netPnlPct >= 0 ? "+" : ""}{netPnlPct.toFixed(2)}%)
          </span>
        </div>
        <div className={styles.timeframes}>
          {[7, 14, 30].map((d) => (
            <button
              key={d}
              className={`${styles.tfBtn} ${days === d ? styles.tfActive : ""}`}
              onClick={() => setDays(d)}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      <div className={styles.statsBar}>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Starting Balance</span>
          <span className={`${styles.statValue} mono`}>${startingBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Current Equity</span>
          <span className={`${styles.statValue} mono text-success`}>${latestEquity.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Peak Balance</span>
          <span className={`${styles.statValue} mono`}>${peakEquity.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Growth Status</span>
          <span className={`${styles.statValue} text-success`}>Profitable Trend ▲</span>
        </div>
      </div>

      <div ref={containerRef} className={styles.chartContainer} />
    </div>
  );
}
