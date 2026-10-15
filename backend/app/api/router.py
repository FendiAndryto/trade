"""
Main router — aggregates all API route modules.
"""

from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.strategies import router as strategies_router
from app.api.trades import router as trades_router
from app.api.webhook import router as webhook_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(webhook_router)
api_router.include_router(strategies_router)
api_router.include_router(trades_router)
api_router.include_router(dashboard_router)

