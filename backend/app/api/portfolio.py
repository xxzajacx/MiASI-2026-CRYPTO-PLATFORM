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
    wallet_type: str = "SPOT"

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    items: List[WalletResponse]

class MessageResponse(BaseModel):
    message: str

class TransferRequest(BaseModel):
    asset: str
    amount: float = Field(..., gt=0)
    from_type: str
    to_type: str

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
        for w_type, balances in binance_balances.items():
            for asset, data in balances.items():
                wallet_list.append(WalletResponse(
                    asset_symbol=asset,
                    balance=data["total"],
                    locked_balance=data["locked"],
                    wallet_type=w_type
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
            locked_balance=w.locked_balance,
            wallet_type=w.wallet_type
        ) for w in wallets]

        return items

@router.post("/transfer", response_model=MessageResponse)
async def transfer_funds(
    req: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Transfer funds between SPOT and FUTURES wallets."""
    # Live users
    if current_user.binance_api_key and "WKLEJ" not in current_user.binance_api_key:
        user_api_key = current_user.binance_api_key or market_data_service.api_key
        user_secret_key = current_user.binance_secret_key or market_data_service.api_secret
        from app.services.market_data import BinanceClient
        user_client = BinanceClient()
        user_client.api_key = user_api_key
        user_client.api_secret = user_secret_key
        user_client.headers = {"X-MBX-APIKEY": user_api_key}
        
        try:
            await user_client.transfer_asset(req.asset, req.amount, req.from_type, req.to_type)
        except Exception as e:
            err_msg = str(e)
            if "404" in err_msg or "Not Found" in err_msg:
                raise HTTPException(
                    status_code=400, 
                    detail="Twoje konto jest podłączone do sieci testowej (Demo). Giełda Binance API nie obsługuje fizycznych transferów pomiędzy środowiskiem Spot Testnet a Futures Testnet. Funkcja transferu działa poprawnie tylko dla rzeczywistych kluczy API (LIVE)."
                )
            raise HTTPException(status_code=400, detail=f"Binance transfer failed: {err_msg}")
            
    else:
        # Simulation
        # Find from_wallet
        res_from = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == req.asset, Wallet.wallet_type == req.from_type))
        wallet_from = res_from.scalars().first()
        if not wallet_from or wallet_from.balance < req.amount:
            raise HTTPException(status_code=400, detail="Niewystarczające środki do przetransferowania")
            
        # Find to_wallet
        res_to = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id, Wallet.asset_symbol == req.asset, Wallet.wallet_type == req.to_type))
        wallet_to = res_to.scalars().first()
        if not wallet_to:
            wallet_to = Wallet(user_id=current_user.id, asset_symbol=req.asset, balance=0.0, locked_balance=0.0, wallet_type=req.to_type)
            db.add(wallet_to)
            
        wallet_from.balance -= req.amount
        wallet_to.balance += req.amount
        
        # Record transaction
        transaction = TransactionHistory(
            user_id=current_user.id,
            type="TRANSFER",
            amount=req.amount,
            asset=req.asset,
            status="COMPLETED",
            log_message=f"Transfer {req.amount} {req.asset} z {req.from_type} do {req.to_type}"
        )
        db.add(transaction)
        await db.commit()
        
    return {"message": "Transfer successful"}

@router.post("/deposit", response_model=MessageResponse)
async def deposit_funds(
    req: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Simulate depositing funds into local wallet (simulation mode only)."""
    # Admin accounts cannot deposit – they are management-only
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konta administracyjne nie mają dostępu do funkcji inwestycyjnych."
        )

    # Live users (with Binance keys) cannot use simulated deposits
    if current_user.binance_api_key and "WKLEJ" not in current_user.binance_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="W trybie LIVE wpłaty środków odbywają się przez giełdę Binance. Funkcja depozytu jest dostępna tylko w trybie symulacji."
        )

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
        log_message=f"Ręczna wpłata {req.amount} {asset}"
    )
    db.add(transaction)
    
    await db.commit()
    
    return {"message": f"Successfully deposited {req.amount} {asset}"}
