import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List

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
    amount: float
    asset: str = "USDT"

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

@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user portfolio from Binance Demo account, fallback to local wallet."""
    
    # Try to get balance from Binance first
    try:
        if not market_data_service.api_key or not market_data_service.api_secret or "WKLEJ" in market_data_service.api_key:
            raise ValueError("Binance API key not configured")
        
        binance_balances = await market_data_service.get_account_balance()
        
        # Convert to response format
        wallet_list = []
        for asset, data in binance_balances.items():
            wallet_list.append(WalletResponse(
                asset_symbol=asset,
                balance=data["total"],
                locked_balance=data["locked"]
            ))
        
        return {"items": wallet_list}
        
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

        return {"items": items}

@router.post("/deposit", response_model=MessageResponse)
async def deposit_funds(
    req: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Simulate depositing funds into local wallet."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get or create wallet for the asset
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == req.asset)
    )
    wallet = result.scalars().first()
    
    if not wallet:
        wallet = Wallet(user_id=current_user.id, asset_symbol=req.asset, balance=0.0, locked_balance=0.0)
        db.add(wallet)
    
    wallet.balance += req.amount
    
    # Record transaction
    transaction = TransactionHistory(
        user_id=current_user.id,
        type="DEPOSIT",
        amount=req.amount,
        asset=req.asset,
        status="COMPLETED",
        log_message=f"Manual deposit of {req.amount} {req.asset}"
    )
    db.add(transaction)
    
    await db.commit()
    
    return {"message": f"Successfully deposited {req.amount} {req.asset}"}
