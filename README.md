# TradeGear 🚀

**No-Code TradingView Automator & Risk Management Dashboard**

> Otomasi sinyal TradingView ke MT5 dengan dashboard modern dan risk management pintar.

---

## 🎯 Apa Ini?

TradeGear menghubungkan strategi TradingView kamu langsung ke MetaTrader 5 tanpa coding.
Webhook dari TradingView → Risk Engine → MT5 execution — semua otomatis dengan dashboard real-time.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐     ┌──────────────┐
│   TradingView   │────▶│         Ubuntu Server (Main)         │────▶│  Windows PC  │
│   (Webhook)     │     │  FastAPI + Next.js + Redis + PgSQL   │     │  MT5 Agent   │
└─────────────────┘     └──────────────────────────────────────┘     └──────────────┘
```

- **Backend**: Python FastAPI (webhook receiver, risk engine, WebSocket)
- **Frontend**: Next.js 16 + TradingView Lightweight Charts
- **Database**: PostgreSQL (multi-tenant)
- **Queue**: Redis + Celery (async webhook processing)
- **MT5 Bridge**: Python agent running on Windows with MT5 terminal

## 📁 Project Structure

```
TRADING/
├── backend/          # FastAPI Backend (Python)
│   ├── app/
│   │   ├── api/      # REST endpoints & WebSocket
│   │   ├── models/   # SQLAlchemy ORM (8 tables)
│   │   ├── schemas/  # Pydantic validation
│   │   ├── services/ # Risk engine, lot calculator
│   │   └── ws/       # WebSocket manager
│   └── pyproject.toml
├── frontend/         # Next.js Dashboard
│   └── src/
│       ├── app/dashboard/  # Dashboard pages
│       └── components/     # UI components
├── mt5-agent/        # MT5 Bridge (Windows)
│   └── agent/        # WebSocket bridge + MT5 client
├── docker-compose.yml  # PostgreSQL + Redis
└── docs/
```

## 🚀 Quick Start

### 1. Start Infrastructure
```bash
docker compose up -d    # PostgreSQL + Redis
```

### 2. Backend
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env    # Edit as needed
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev             # http://localhost:3000
```

### 4. MT5 Agent (Windows only)
```bash
cd mt5-agent
pip install -e .
# Set environment variables (MT5_LOGIN, MT5_PASSWORD, etc.)
python -m agent.main
```

## 📊 Features

### ✅ Built & Connected (Phase 1 & Phase 2)
- [x] Dashboard with live candlestick chart (XAUUSD) & Equity Growth Curve
- [x] Real-time stat cards (Balance, Equity, P&L, Daily Loss)
- [x] Active trades panel with live P&L calculation & instant manual close
- [x] Dynamic Risk monitor (daily loss meter, open trades meter, auto-status)
- [x] Recent webhooks audit feed with real-time popup toasts
- [x] Full REST API (auth, strategies, trades, webhooks, dashboard summary)
- [x] Real-time WebSocket hub (tick stream, webhook logs, remote order execution)
- [x] Pre-trade Risk Engine (lot sizing, daily loss limit, max concurrent trades)
- [x] MT5 agent with auto-reconnect WebSocket bridge
- [x] Multi-tenant PostgreSQL database with Alembic migrations (8 tables)
- [x] Full Next.js 16 frontend with authentication (login & register)
- [x] Strategy Management UI with webhook URL & PineScript payload generator
- [x] Risk Management & Circuit Breakers UI with Emergency Kill-Switch
- [x] Trades History & Positions Page with filters & ticket tracking
- [x] TradingView Webhook Audit Logs Page with JSON payload viewer
- [x] MetaTrader 5 Terminal Monitor & Bridge Setup guide
- [x] Pytest unit test suite & Ruff clean linting

### 🔜 Next Up (Phase 3-5)
- [ ] Celery worker for async webhook processing
- [ ] Email/Telegram notifications on execution & risk alerts
- [ ] EA plugin (.ex5) for SaaS scaling without python agent
- [ ] Multiple MT5 account portfolio switching

## 🔑 API Quick Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login → JWT tokens |
| `/api/v1/webhook/{strategy_id}` | POST | Receive TradingView alert |
| `/api/v1/strategies` | GET/POST | List/create strategies |
| `/api/v1/trades` | GET | List trades (paginated) |
| `/api/v1/dashboard/summary` | GET | Dashboard stats |
| `/ws?token=<jwt>` | WS | Real-time updates |

## 📝 License

Private — All rights reserved.
