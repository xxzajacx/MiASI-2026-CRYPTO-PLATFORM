import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

from app.api.auth import get_current_user
from app.models.user import User
from app.services.market_data import market_data_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.wallet import Wallet
from app.models.transaction import TransactionHistory

logger = logging.getLogger(__name__)

router = APIRouter()

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    asset: Optional[str] = None
    asset_symbol: Optional[str] = None

class WalletResponse(BaseModel):
    asset_symbol: str
    balance: float
    locked_balance: float

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    items: List[WalletResponse]

class MessageResponse(BaseModel):
    message: str

@router.get("/", response_model=List[WalletResponse])
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user portfolio from Binance Demo account, fallback to local wallet."""
    
    # Try to get balance from Binance first
    try:
        user_api_key = current_user.binance_api_key or market_data_service.api_key
        user_secret_key = current_user.binance_secret_key or market_data_service.api_secret

        if not user_api_key or not user_secret_key or "WKLEJ" in user_api_key:
            raise ValueError("Binance API key not configured")
        
        if current_user.binance_api_key:
            from app.services.market_data import BinanceClient
            user_client = BinanceClient()
            user_client.api_key = user_api_key
            user_client.api_secret = user_secret_key
            user_client.headers = {"X-MBX-APIKEY": user_api_key}
            binance_balances = await user_client.get_account_balance()
        else:
            binance_balances = await market_data_service.get_account_balance()
        
        # Convert to response format
        wallet_list = []
        for asset, data in binance_balances.items():
            wallet_list.append(WalletResponse(
                asset_symbol=asset,
                balance=data["total"],
                locked_balance=data["locked"]
            ))
        
        return wallet_list
        
    except Exception as e:
        logger.warning(f"Failed to fetch Binance balance, using local fallback: {e}")
        
        # Fallback to local wallet if Binance fails
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id)
        )
        wallets = result.scalars().all()
        
        items = [WalletResponse(
            asset_symbol=w.asset_symbol,
            balance=w.balance,
            locked_balance=w.locked_balance
        ) for w in wallets]

        return items

@router.post("/deposit", response_model=MessageResponse)
async def deposit_funds(
    req: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Simulate depositing funds into local wallet."""
    asset = req.asset_symbol or req.asset or "USDT"
    
    # Get or create wallet for the asset
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == asset)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        wallet = Wallet(user_id=current_user.id, asset_symbol=asset, balance=0.0, locked_balance=0.0)
        db.add(wallet)
    
    wallet.balance += req.amount
    
    # Record transaction
    transaction = TransactionHistory(
        user_id=current_user.id,
        type="DEPOSIT",
        amount=req.amount,
        asset=asset,
        status="COMPLETED",
        log_message=f"Manual deposit of {req.amount} {asset}"
    )
    db.add(transaction)
    
    await db.commit()
    
    return {"message": f"Successfully deposited {req.amount} {asset}"}
