from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from app.services.market_data import market_data_service
from app.services.email_service import (
    generate_confirmation_code,
    send_confirmation_email,
    store_pending_confirmation,
    verify_confirmation,
    requires_email_confirmation,
)
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
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None

class ConfirmTradeRequest(BaseModel):
    confirmation_token: str
    confirmation_code: str

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
    """Execute a trade (BUY/SELL) at market price, optionally with TP/SL.

    For high-value trades (above EMAIL_CONFIRM_THRESHOLD USDT),
    an email confirmation code is required before execution.
    """
    return await _execute_trade_internal(req, current_user, db, skip_email_check=False)


async def _execute_trade_internal(
    req: TradeRequest,
    current_user: User,
    db: AsyncSession,
    skip_email_check: bool = False
):
    """Core trade execution logic shared by /trade and /trade/confirm."""
    req.side = req.side.upper()
    if req.side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
    
    # Basic Validation
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Ilość musi być większa od zera")

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

    # Email confirmation gate for high-value trades
    if not skip_email_check and requires_email_confirmation(notional_value):
        if current_user.email:
            code = generate_confirmation_code()
            trade_details = (
                f"{req.side} {req.amount} {req.symbol} "
                f"(~{notional_value:.2f} USDT, {req.leverage}x leverage)"
            )
            token = store_pending_confirmation(
                user_id=current_user.id,
                code=code,
                trade_data=req.model_dump(),
            )
            await send_confirmation_email(
                to_email=current_user.email,
                username=current_user.username,
                code=code,
                trade_details=trade_details,
            )
            return TradeResponse(
                success=False,
                message=f"Transakcja wymaga potwierdzenia e-mail. Kod wysłany na {current_user.email}.",
                price=current_price,
                amount=req.amount,
                total_cost=notional_value,
                requires_confirmation=True,
                confirmation_token=token,
            )
        else:
            logger.info(f"User {current_user.username} has no email – skipping email confirmation for high-value trade")

    # Handle USDT amount conversion
    if req.amount_type == "usdt":
        req.amount = req.amount / current_price

    base_asset = req.symbol.replace("USDT", "")
    quote_asset = "USDT"
    total_cost = req.amount * current_price if req.side == "BUY" else req.amount

    # Attempt Binance trade — prefer user's personal keys, fallback to global
    binance_success = False
    binance_order_id = None
    
    # Determine which API keys to use
    user_api_key = current_user.binance_api_key or market_data_service.api_key
    user_secret_key = current_user.binance_secret_key or market_data_service.api_secret
    
    if user_api_key and "WKLEJ" not in user_api_key:
        try:
            # If user has personal keys, create a temporary client for this trade
            if current_user.binance_api_key:
                from app.services.market_data import BinanceClient
                user_client = BinanceClient()
                user_client.api_key = user_api_key
                user_client.api_secret = user_secret_key
                user_client.headers = {"X-MBX-APIKEY": user_api_key}
                result = await user_client.execute_trade(
                    req.symbol, req.side, req.amount, req.leverage
                )
            else:
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
    
    return TradeResponse(
        success=True,
        message=f"Successfully executed {req.side} order",
        price=current_price,
        amount=req.amount,
        total_cost=req.amount * current_price,
        order_id=binance_order_id,
    )

@router.get("/status")
async def get_market_status(current_user: User = Depends(get_current_user)):
    user_api_key = current_user.binance_api_key or market_data_service.api_key
    user_secret_key = current_user.binance_secret_key or market_data_service.api_secret
    
    is_live = bool(
        user_api_key and 
        user_secret_key and 
        "WKLEJ" not in user_api_key
    )
    return {
        "status": "online",
        "binance_connected": is_live,
        "symbols": [s.strip() for s in settings.TRACKED_SYMBOLS.split(",")],
        "min_order_sizes": market_data_service.MIN_ORDER_SIZES
    }


@router.post("/trade/confirm", response_model=TradeResponse)
async def confirm_trade(
    req: ConfirmTradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Confirm a high-value trade using the email verification code.

    This endpoint is called after the user receives an email with
    a 6-digit confirmation code for trades exceeding the threshold.
    """
    trade_data = verify_confirmation(
        req.confirmation_token, req.confirmation_code, current_user.id
    )
    if not trade_data:
        raise HTTPException(
            status_code=400,
            detail="Nieprawidłowy lub wygasły kod potwierdzenia. Spróbuj ponownie."
        )

    # Reconstruct the original TradeRequest from stored data
    original_req = TradeRequest(**trade_data)
    # Re-use the execute_trade logic but skip the email check
    return await _execute_trade_internal(original_req, current_user, db, skip_email_check=True)
