from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from app.services.market_data import market_data_service
from app.api.auth import get_current_user
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import TransactionHistory
from app.models.order import Order
from app.core.database import get_db
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

class TradeRequest(BaseModel):
    symbol: str
    side: str  # 'BUY' or 'SELL'
    amount: float
    amount_type: str = "crypto"  # 'crypto' or 'usdt'
    leverage: int = 1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradeResponse(BaseModel):
    success: bool
    message: str
    price: float
    amount: float
    total_cost: float
    order_id: Optional[str] = None

class PricesResponse(BaseModel):
    prices: Dict[str, float]

class PriceResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    error: Optional[str] = None

@router.get("/prices", response_model=PricesResponse)
async def get_current_prices():
    prices = await market_data_service.get_all_prices()
    return {"prices": prices}

@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str):
    price = market_data_service.get_price(symbol)
    if price is None:
        return {"symbol": symbol, "price": None, "error": "Symbol not found or data not fetched yet"}
    return {"symbol": symbol, "price": price, "error": None}

@router.post("/trade", response_model=TradeResponse)
async def execute_trade(
    req: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a trade (BUY/SELL) at market price, optionally with TP/SL."""
    req.side = req.side.upper()
    if req.side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    
    # Basic Validation
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Ilość musi być większa od zera")
    
    if req.side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Nieprawidłowa strona transakcji")

    current_price = market_data_service.get_price(req.symbol)
    if not current_price:
        await market_data_service.refresh()
        current_price = market_data_service.get_price(req.symbol)
        if not current_price:
            raise HTTPException(status_code=503, detail="Current price not available")

    # Minimum Notional Check (e.g. 5 USDT)
    notional_value = req.amount if req.amount_type == "usdt" else (req.amount * current_price)
    if notional_value < 5:
        raise HTTPException(status_code=400, detail=f"Wartość zlecenia jest za niska. Minimum to 5 USDT (Obecnie: {notional_value:.2f} USDT)")

    # Handle USDT amount conversion
    if req.amount_type == "usdt":
        req.amount = req.amount / current_price

    base_asset = req.symbol.replace("USDT", "")
    quote_asset = "USDT"
    total_cost = req.amount * current_price if req.side == "BUY" else req.amount

    # Attempt Binance trade if keys are present
    binance_success = False
    binance_order_id = None
    
    if market_data_service.api_key and "WKLEJ" not in market_data_service.api_key:
        try:
            result = await market_data_service.execute_trade(
                req.symbol, req.side, req.amount, req.leverage
            )
            binance_success = True
            binance_order_id = str(result.get("orderId", result.get("order_id", "")))
        except Exception as e:
            error_msg = str(e)
            if "Margin is insufficient" in error_msg or "-2019" in error_msg:
                raise HTTPException(
                    status_code=400, 
                    detail="Brak środków na koncie Binance Futures. Zaloguj się na demo.binance.com i przelej USDT z portfela Spot do Futures."
                )
            logger.warning(f"Binance trade failed, falling back to local: {e}")

    # Local Wallet logic (always update local wallet as a shadow or fallback)
    fee_rate = 0.001 # 0.1% fee
    
    if req.side == "BUY":
        # Check USDT balance with leverage
        res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == quote_asset))
        usdt_wallet = res.scalars().first()
        
        total_value = req.amount * current_price
        required_margin = total_value / req.leverage
        fee = total_value * fee_rate
        
        if not usdt_wallet or usdt_wallet.balance < (required_margin + fee):
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient USDT balance for margin. Need {required_margin + fee:.2f}, have {usdt_wallet.balance if usdt_wallet else 0:.2f}"
            )
        
        usdt_wallet.balance -= (required_margin + fee)
        
        # Add to base asset wallet
        res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == base_asset))
        asset_wallet = res.scalars().first()
        if not asset_wallet:
            asset_wallet = Wallet(user_id=current_user.id, asset_symbol=base_asset, balance=0.0, locked_balance=0.0)
            db.add(asset_wallet)
        asset_wallet.balance += req.amount

    else: # SELL
        # Check base asset balance
        res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == base_asset))
        asset_wallet = res.scalars().first()
        
        if not asset_wallet or asset_wallet.balance < req.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient {base_asset} balance. Have: {asset_wallet.balance if asset_wallet else 0}")
        
        asset_wallet.balance -= req.amount
        
        # Add to USDT wallet
        res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == quote_asset))
        usdt_wallet = res.scalars().first()
        if not usdt_wallet:
            usdt_wallet = Wallet(user_id=current_user.id, asset_symbol=quote_asset, balance=0.0, locked_balance=0.0)
            db.add(usdt_wallet)
            
        total_value = req.amount * current_price
        fee = total_value * fee_rate
        
        usdt_wallet.balance += (total_value - fee)

    # Record transaction
    transaction = TransactionHistory(
        user_id=current_user.id,
        type=req.side,
        amount=req.amount,
        asset=base_asset,
        price=current_price,
        status="COMPLETED",
        log_message=f"Market {req.side} of {req.amount} {base_asset} at {current_price} ({req.leverage}x leverage)"
    )
    db.add(transaction)

    # Handle TP/SL
    if req.stop_loss or req.take_profit:
        # Validation
        if req.side == "BUY":
            if req.stop_loss and req.stop_loss >= current_price:
                raise HTTPException(status_code=400, detail="Stop Loss for BUY must be lower than current price")
            if req.take_profit and req.take_profit <= current_price:
                raise HTTPException(status_code=400, detail="Take Profit for BUY must be higher than current price")
        else: # SELL
            if req.stop_loss and req.stop_loss <= current_price:
                raise HTTPException(status_code=400, detail="Stop Loss for SELL must be higher than current price")
            if req.take_profit and req.take_profit >= current_price:
                raise HTTPException(status_code=400, detail="Take Profit for SELL must be lower than current price")

        if req.stop_loss or req.take_profit:
            group_id = str(uuid.uuid4())
            if req.stop_loss:
                sl_order = Order(
                    user_id=current_user.id,
                    symbol=req.symbol,
                    order_type="STOP_LOSS",
                    side="SELL" if req.side == "BUY" else "BUY",
                    amount=req.amount,
                    target_price=req.stop_loss,
                    leverage=req.leverage,
                    group_id=group_id,
                    status="ACTIVE"
                )
                db.add(sl_order)
            if req.take_profit:
                tp_order = Order(
                    user_id=current_user.id,
                    symbol=req.symbol,
                    order_type="TAKE_PROFIT",
                    side="SELL" if req.side == "BUY" else "BUY",
                    amount=req.amount,
                    target_price=req.take_profit,
                    leverage=req.leverage,
                    group_id=group_id,
                    status="ACTIVE"
                )
                db.add(tp_order)

    await db.commit()
    
    return {
        "success": True,
        "message": f"Successfully executed {req.side} order",
        "price": current_price,
        "amount": req.amount,
        "total_cost": req.amount * current_price if req.side == "BUY" else req.amount * current_price,
        "order_id": binance_order_id
    }

@router.get("/status")
async def get_market_status():
    is_live = (
        market_data_service.api_key and 
        market_data_service.api_secret and 
        "WKLEJ" not in market_data_service.api_key
    )
    return {
        "status": "online",
        "binance_connected": bool(is_live),
        "symbols": [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")],
        "min_order_sizes": market_data_service.MIN_ORDER_SIZES
    }
