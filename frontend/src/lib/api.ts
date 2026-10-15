/**
 * TradeGear API Client
 * Robust client with JWT auth injection, error handling, and type safety.
 */

import {
  DailyStatItem,
  DashboardSummary,
  EquityCurveResponse,
  RiskProfile,
  Strategy,
  TokenResponse,
  Trade,
  User,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("tg_access_token");
}

function setStoredTokens(tokens: TokenResponse): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("tg_access_token", tokens.access_token);
  localStorage.setItem("tg_refresh_token", tokens.refresh_token);
}

function clearStoredTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("tg_access_token");
  localStorage.removeItem("tg_refresh_token");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const token = getStoredToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401 && typeof window !== "undefined") {
    // Attempt refresh if refresh token is available
    const refreshToken = localStorage.getItem("tg_refresh_token");
    if (refreshToken && !endpoint.includes("/auth/refresh") && !endpoint.includes("/auth/login")) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const newTokens: TokenResponse = await refreshRes.json();
          setStoredTokens(newTokens);
          headers["Authorization"] = `Bearer ${newTokens.access_token}`;
          const retryRes = await fetch(url, { ...options, headers });
          if (!retryRes.ok) {
            throw new ApiError(retryRes.statusText, retryRes.status);
          }
          if (retryRes.status === 204) return null as T;
          return (await retryRes.json()) as T;
        } else {
          clearStoredTokens();
        }
      } catch {
        clearStoredTokens();
      }
    }
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || JSON.stringify(errorJson);
    } catch {
      // fallback
    }
    throw new ApiError(errorDetail, response.status);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: "DELETE" }),

  // Auth endpoints
  auth: {
    login: async (email: string, password: string): Promise<TokenResponse> => {
      const res = await request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setStoredTokens(res);
      return res;
    },
    register: async (
      email: string,
      password: string,
      displayName: string
    ): Promise<User> => {
      return request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          display_name: displayName,
        }),
      });
    },
    me: (): Promise<User> => request<User>("/auth/me"),
    logout: () => {
      clearStoredTokens();
    },
    hasToken: (): boolean => !!getStoredToken(),
  },

  // Dashboard endpoints
  dashboard: {
    getSummary: (): Promise<DashboardSummary> =>
      request<DashboardSummary>("/dashboard/summary"),
    getWebhooks: (limit?: number): Promise<any[]> =>
      request<any[]>(`/dashboard/webhooks${limit ? `?limit=${limit}` : ""}`),
    getEquityCurve: (days: number = 30): Promise<EquityCurveResponse> =>
      request<EquityCurveResponse>(`/dashboard/equity-curve?days=${days}`),
    getDailyStats: (days: number = 30): Promise<DailyStatItem[]> =>
      request<DailyStatItem[]>(`/dashboard/daily-stats?days=${days}`),
    seedDemo: (): Promise<{ message: string; status: string }> =>
      request<{ message: string; status: string }>("/dashboard/seed-demo", {
        method: "POST",
      }),
  },

  // Trade endpoints
  trades: {
    list: (params?: { page?: number; per_page?: number; status?: string }): Promise<{ trades: Trade[]; total: number }> => {
      const query = new URLSearchParams();
      if (params?.page) query.append("page", params.page.toString());
      if (params?.per_page) query.append("per_page", params.per_page.toString());
      if (params?.status) query.append("status", params.status);
      const qs = query.toString();
      return request<{ trades: Trade[]; total: number }>(`/trades${qs ? `?${qs}` : ""}`);
    },
    close: (tradeId: string): Promise<Trade> =>
      request<Trade>(`/trades/${tradeId}/close`, { method: "POST" }),
  },

  // Strategy endpoints
  strategies: {
    list: (): Promise<Strategy[]> => request<Strategy[]>("/strategies"),
    create: (data: Partial<Strategy>): Promise<Strategy> =>
      request<Strategy>("/strategies", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Strategy>): Promise<Strategy> =>
      request<Strategy>(`/strategies/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    updateRisk: (id: string, data: Partial<RiskProfile>): Promise<RiskProfile> =>
      request<RiskProfile>(`/strategies/${id}/risk`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string): Promise<void> =>
      request<void>(`/strategies/${id}`, { method: "DELETE" }),
  },
};

export { ApiError, getStoredToken, setStoredTokens, clearStoredTokens };
