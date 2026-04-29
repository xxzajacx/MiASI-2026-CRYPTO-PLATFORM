from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.order import Order
from app.services.market_data import market_data_service
from app.core.config import settings

router = APIRouter()

class OrderCreate(BaseModel):
    symbol: str
    order_type: str # 'STOP_LOSS' | 'TAKE_PROFIT'
    amount: float
    target_price: float

class OrderResponse(BaseModel):
    id: int
    symbol: str
    order_type: str
    amount: float
    target_price: float
    status: str

    class Config:
        from_attributes = True

class PaginatedOrderResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    limit: int
    offset: int

class MessageResponse(BaseModel):
    message: str

@router.get("/", response_model=PaginatedOrderResponse)
async def get_orders(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get total count of user's orders
    total_result = await db.execute(
        select(func.count(Order.id)).filter(Order.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    # Get paginated order items
    result = await db.execute(
        select(Order)
        .filter(Order.user_id == current_user.id)
        .limit(limit)
        .offset(offset)
    )
    orders = result.scalars().all()

    return {
        "items": orders,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_req: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate order type
    if order_req.order_type not in ["STOP_LOSS", "TAKE_PROFIT"]:
        raise HTTPException(status_code=400, detail="Invalid order type. Must be STOP_LOSS or TAKE_PROFIT")
    
    # Validate positive values
    if order_req.amount <= 0 or order_req.target_price <= 0:
        raise HTTPException(status_code=400, detail="Amount and target price must be positive")

    # Validate tracked symbol
    tracked_symbols = [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")]
    if order_req.symbol not in tracked_symbols:
        raise HTTPException(status_code=400, detail="Symbol not supported")

    # Get current market price for the symbol
    current_price = market_data_service.get_price(order_req.symbol)
    if current_price is None:
        # Try to refresh prices if not cached
        await market_data_service.refresh()
        current_price = market_data_service.get_price(order_req.symbol)
        if current_price is None:
            raise HTTPException(status_code=503, detail="Unable to fetch current price for symbol")

    # Validate target price makes sense
    if order_req.order_type == "STOP_LOSS":
        if order_req.target_price >= current_price:
            raise HTTPException(
                status_code=400,
                detail="Invalid target price for STOP_LOSS: must be lower than current market price"
            )
    elif order_req.order_type == "TAKE_PROFIT":
        if order_req.target_price <= current_price:
            raise HTTPException(
                status_code=400,
                detail="Invalid target price for TAKE_PROFIT: must be higher than current market price"
            )

    # Check user has sufficient balance on Binance
    try:
        binance_balances = await market_data_service.get_account_balance()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to verify balance with Binance: {str(e)}")

    # Extract base asset (e.g., BTC from BTCUSDT)
    base_asset = order_req.symbol.replace("USDT", "")
    asset_balance = binance_balances.get(base_asset, {"free": 0.0, "locked": 0.0})
    free_balance = asset_balance["free"]

    if free_balance < order_req.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Musisz najpierw kupić krypto. Insufficient {base_asset} balance on Binance. Available: {free_balance}, Required: {order_req.amount}"
        )

    # Create order record
    new_order = Order(
        user_id=current_user.id,
        symbol=order_req.symbol,
        order_type=order_req.order_type,
        amount=order_req.amount,
        target_price=order_req.target_price,
        status="ACTIVE"
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order

@router.delete("/{order_id}", response_model=MessageResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Order).filter(Order.id == order_id, Order.user_id == current_user.id))
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Only active orders can be cancelled")

    # Update order status to cancelled
    order.status = "CANCELLED"
    await db.commit()

    return {"message": "Order cancelled successfully"}
