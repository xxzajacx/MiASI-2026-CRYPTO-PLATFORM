from fastapi import APIRouter
from .auth import router as auth_router
from .orders import router as orders_router
from .portfolio import router as portfolio_router
from .market import router as market_router
from .transactions import router as transactions_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
