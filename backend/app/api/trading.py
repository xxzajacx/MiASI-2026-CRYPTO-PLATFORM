import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.api.auth import get_current_user
from app.models.user import User
from app.models.transaction import TransactionHistory
from app.services.market_data import market_data_service

logger = logging.getLogger(__name__)

router = APIRouter()

class MarketOrderRequest(BaseModel):
    symbol: str
    quantity: float

class OrderExecutionResponse(BaseModel):
    success: bool
    order_id: int
    symbol: str
    executed_qty: float
    total_cost: float
    message: str

@router.post("/buy", response_model=OrderExecutionResponse)
async def market_buy(
    order_req: MarketOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute a market buy order on Binance Demo."""
    # Validate symbol
    tracked_symbols = [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")]
    if order_req.symbol not in tracked_symbols:
        raise HTTPException(status_code=400, detail=f"Symbol {order_req.symbol} not supported")
    
    try:
        binance_order = await market_data_service.execute_market_buy(
            symbol=order_req.symbol,
            quantity=order_req.quantity
        )
    except Exception as e:
        logger.error(f"Failed to execute buy order: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to execute order on Binance: {str(e)}")

    # Log transaction to local DB
    async with AsyncSessionLocal() as db:
        transaction = TransactionHistory(
            user_id=current_user.id,
            order_id=None,
            type="BUY",
            amount=binance_order["executed_qty"],
            asset=order_req.symbol,
            price=binance_order["cummulative_quote_qty"] / binance_order["executed_qty"] if binance_order["executed_qty"] > 0 else 0,
            fee=sum(float(fill.get("commission", 0)) for fill in binance_order["fills"]),
            status="COMPLETED",
            log_message=f"Binance market buy order {binance_order['order_id']}"
        )
        db.add(transaction)
        await db.commit()

    return OrderExecutionResponse(
        success=True,
        order_id=binance_order["order_id"],
        symbol=binance_order["symbol"],
        executed_qty=binance_order["executed_qty"],
        total_cost=binance_order["cummulative_quote_qty"],
        message=f"Successfully bought {binance_order['executed_qty']} {order_req.symbol.replace('USDT', '')}"
    )

@router.post("/market-sell", response_model=OrderExecutionResponse)
async def market_sell(
    order_req: MarketOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute a market sell order on Binance Demo."""
    tracked_symbols = [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")]
    if order_req.symbol not in tracked_symbols:
        raise HTTPException(status_code=400, detail=f"Symbol {order_req.symbol} not supported")
    
    try:
        binance_order = await market_data_service.execute_market_sell(
            symbol=order_req.symbol,
            quantity=order_req.quantity
        )
    except Exception as e:
        logger.error(f"Failed to execute sell order: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to execute order on Binance: {str(e)}")

    # Process fills
    fills = binance_order.get("fills", [])
    total_qty = sum(float(fill["qty"]) for fill in fills)
    total_value = sum(float(fill["qty"]) * float(fill["price"]) for fill in fills)
    executed_price = total_value / total_qty if total_qty > 0 else 0
    total_fee = sum(float(fill.get("commission", 0)) for fill in fills)

    # Log transaction
    async with AsyncSessionLocal() as db:
        transaction = TransactionHistory(
            user_id=current_user.id,
            order_id=None,
            type="SELL",
            amount=total_qty,
            asset=order_req.symbol,
            price=executed_price,
            fee=total_fee,
            status="COMPLETED",
            log_message=f"Binance market sell order {binance_order.get('orderId')}"
        )
        db.add(transaction)
        await db.commit()

    return OrderExecutionResponse(
        success=True,
        order_id=binance_order.get("orderId"),
        symbol=binance_order.get("symbol"),
        executed_qty=total_qty,
        total_cost=total_value,
        message=f"Successfully sold {total_qty} {order_req.symbol.replace('USDT', '')}"
    )
