"""
FastAPI Application Entry Point — TradeGear Backend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.websocket import router as ws_router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    import asyncio
    from app.services.autonomous_runner import run_autonomous_strategy_engine

    # --- Startup ---
    print(f"[*] {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"[*] Debug mode: {settings.DEBUG}")
    auto_task = asyncio.create_task(run_autonomous_strategy_engine())
    yield
    # --- Shutdown ---
    print(f"[*] {settings.APP_NAME} shutting down...")
    auto_task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="No-Code TradingView Automator & Risk Management Dashboard",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
