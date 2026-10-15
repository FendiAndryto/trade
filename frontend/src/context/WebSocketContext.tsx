"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { useAuth } from "./AuthContext";
import { api, getStoredToken } from "@/lib/api";

export interface MarketTick {
  symbol: string;
  bid: number;
  ask: number;
  time: string;
  prevBid?: number;
  direction?: "up" | "down" | "flat";
}

export interface WebhookLogItem {
  id: string;
  strategy_id?: string;
  action: string;
  symbol: string;
  status: "executed" | "rejected" | "received" | "failed";
  message: string;
  processing_ms?: number;
  received_at: string;
}

export interface ToastMessage {
  id: string;
  title: string;
  message: string;
  type: "success" | "danger" | "warning" | "info";
  timestamp: number;
}

export interface AccountUpdateData {
  login?: number;
  server?: string;
  company?: string;
  currency?: string;
  balance?: number;
  equity?: number;
  margin?: number;
  margin_free?: number;
  margin_level?: number;
}

interface WebSocketContextType {
  isConnected: boolean;
  isConnecting: boolean;
  ticks: Record<string, MarketTick>;
  recentWebhooks: WebhookLogItem[];
  toasts: ToastMessage[];
  accountUpdate: AccountUpdateData | null;
  dismissToast: (id: string) => void;
  subscribe: (symbols: string[]) => void;
  closeTrade: (tradeId: string) => void;
  addToast: (toast: Omit<ToastMessage, "id" | "timestamp">) => void;
  refreshWebhooks: () => Promise<void>;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(
  undefined
);

const getWsUrl = () => {
  if (process.env.NEXT_PUBLIC_WS_URL && !process.env.NEXT_PUBLIC_WS_URL.includes("localhost:8001")) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws`;
  }
  return "wss://trade.homever.my.id/ws";
};

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { token, isAuthenticated } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [ticks, setTicks] = useState<Record<string, MarketTick>>({});
  const [recentWebhooks, setRecentWebhooks] = useState<WebhookLogItem[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [accountUpdate, setAccountUpdate] = useState<AccountUpdateData | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const subscribedSymbolsRef = useRef<Set<string>>(
    new Set(["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD"])
  );

  const addToast = useCallback(
    (toast: Omit<ToastMessage, "id" | "timestamp">) => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastMessage = {
        ...toast,
        id,
        timestamp: Date.now(),
      };
      setToasts((prev) => [newToast, ...prev].slice(0, 5));

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const refreshWebhooks = useCallback(async () => {
    try {
      const logs = await api.dashboard.getWebhooks(15);
      if (logs && Array.isArray(logs) && logs.length > 0) {
        const formatted: WebhookLogItem[] = logs.map((l: any) => ({
          id: l.id,
          strategy_id: l.strategy_id,
          action: l.raw_payload?.action?.toUpperCase() || "ALERT",
          symbol: l.raw_payload?.symbol?.toUpperCase() || "XAUUSD",
          status: l.status?.toLowerCase() || "executed",
          message:
            l.rejection_reason ||
            l.raw_payload?.comment ||
            `Webhook signal processed (${l.processing_ms ?? 35}ms)`,
          processing_ms: l.processing_ms ?? 35,
          received_at: l.received_at,
        }));
        setRecentWebhooks(formatted);
      }
    } catch {
      // Keep existing
    }
  }, []);

  useEffect(() => {
    refreshWebhooks();
  }, [refreshWebhooks]);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const currentToken = token || getStoredToken() || "dev";
    setIsConnecting(true);

    try {
      const socket = new WebSocket(`${getWsUrl()}?token=${encodeURIComponent(currentToken)}`);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);

        // Subscribe to initial symbols
        const symbols = Array.from(subscribedSymbolsRef.current);
        socket.send(
          JSON.stringify({
            event: "subscribe",
            data: { symbols },
          })
        );

        // Start heartbeat ping
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ event: "ping" }));
          }
        }, 15000);
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const ev = payload.event;
          const data = payload.data;

          if (ev === "tick" && data) {
            setTicks((prev) => {
              const prevTick = prev[data.symbol];
              const prevBid = prevTick ? prevTick.bid : data.bid;
              const direction =
                data.bid > prevBid ? "up" : data.bid < prevBid ? "down" : "flat";

              return {
                ...prev,
                [data.symbol]: {
                  symbol: data.symbol,
                  bid: data.bid,
                  ask: data.ask,
                  time: data.time || new Date().toISOString(),
                  prevBid,
                  direction,
                },
              };
            });
          } else if (ev === "webhook.log" && data) {
            const newEntry: WebhookLogItem = {
              id: data.id || `${Date.now()}`,
              strategy_id: data.strategy_id,
              action: data.action?.toUpperCase() || "TRADE",
              symbol: data.symbol?.toUpperCase() || "XAUUSD",
              status: data.status || "executed",
              message: data.message || "Webhook signal received",
              processing_ms: data.processing_ms ?? 40,
              received_at: data.received_at || new Date().toISOString(),
            };

            setRecentWebhooks((prev) => [newEntry, ...prev.slice(0, 19)]);

            // Trigger real-time visual toast
            addToast({
              title: `⚡ Webhook: ${newEntry.action} ${newEntry.symbol}`,
              message: newEntry.message,
              type:
                newEntry.status === "executed"
                  ? "success"
                  : newEntry.status === "rejected"
                  ? "danger"
                  : "info",
            });
          } else if (ev === "account_update" && data) {
            setAccountUpdate(data);
          } else if (ev === "trade.closed" && data) {
            addToast({
              title: "Trade Closed",
              message: `Position #${data.trade_id.slice(0, 8)} closed successfully.`,
              type: "info",
            });
          }
        } catch {
          // Ignore JSON parse error
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        // Auto-reconnect after 3s
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };

      socket.onerror = () => {
        socket.close();
      };
    } catch {
      setIsConnected(false);
      setIsConnecting(false);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 4000);
    }
  }, [token, addToast]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const subscribe = useCallback((symbols: string[]) => {
    symbols.forEach((s) => subscribedSymbolsRef.current.add(s.toUpperCase()));
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "subscribe",
          data: { symbols },
        })
      );
    }
  }, []);

  const closeTrade = useCallback((tradeId: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "close_trade",
          data: { trade_id: tradeId },
        })
      );
    }
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        isConnecting,
        ticks,
        recentWebhooks,
        toasts,
        accountUpdate,
        dismissToast,
        subscribe,
        closeTrade,
        addToast,
        refreshWebhooks,
      }}
    >
      {children}
      {/* Real-time Toast Overlay */}
      {toasts.length > 0 && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            maxWidth: "380px",
            pointerEvents: "none",
          }}
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              style={{
                pointerEvents: "auto",
                background: "var(--bg-card)",
                border: `1px solid ${
                  toast.type === "success"
                    ? "var(--color-success-border)"
                    : toast.type === "danger"
                    ? "var(--color-danger-border)"
                    : "var(--border-accent)"
                }`,
                borderLeft: `4px solid ${
                  toast.type === "success"
                    ? "var(--color-success)"
                    : toast.type === "danger"
                    ? "var(--color-danger)"
                    : "var(--accent-blue)"
                }`,
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.45)",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
                animation: "toastSlideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
                backdropFilter: "blur(12px)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    fontSize: "var(--text-sm)",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                  }}
                >
                  {toast.title}
                </span>
                <button
                  onClick={() => dismissToast(toast.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "14px",
                    lineHeight: 1,
                  }}
                >
                  ✕
                </button>
              </div>
              <span
                style={{
                  fontSize: "var(--text-xs)",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                }}
              >
                {toast.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
}
