import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timedelta, date

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.order import Order
from app.models.transaction import TransactionHistory
from app.models.wallet import Wallet
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["admin"])


# Dependency to check if user is admin
async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# Pydantic models
class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    is_active: bool
    is_admin: bool
    failed_login_attempts: int
    locked_until: Optional[str] = None
    birth_date: date

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    wallets: List[dict]
    active_orders_count: int


class BlockUserRequest(BaseModel):
    reason: Optional[str] = None
    lock_duration_days: int = 1  # 0 = permanent ban


class ResetPasswordRequest(BaseModel):
    new_password: str


class UpdateConfigRequest(BaseModel):
    trading_fee_rate: Optional[float] = None
    tracked_symbols: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    username: str
    order_id: Optional[int]
    type: str
    amount: float
    asset: str
    price: Optional[float] = None
    fee: Optional[float] = None
    status: str
    log_message: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the system."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific user."""
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user wallets
    wallets_result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
    wallets = wallets_result.scalars().all()
    wallets_data = [{"asset": w.asset_symbol, "balance": w.balance, "locked": w.locked_balance} for w in wallets]
    
    # Get active orders count
    orders_result = await db.execute(
        select(func.count(Order.id)).filter(Order.user_id == user_id, Order.status == "ACTIVE")
    )
    active_orders_count = orders_result.scalar_one()
    
    return {
        **UserResponse.from_orm(user).dict(),
        "wallets": wallets_data,
        "active_orders_count": active_orders_count
    }


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    block_req: BlockUserRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Block a user account."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot block your own account")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    
    if block_req.lock_duration_days == 0:
        # Permanent ban
        user.locked_until = "PERMANENT"
        await db.commit()
        logger.info(f"Admin {admin.username} permanently banned user {user.username}")
        return {"message": f"Użytkownik {user.username} został permanentnie zablokowany."}
    else:
        lock_until = datetime.utcnow() + timedelta(days=block_req.lock_duration_days)
        user.locked_until = lock_until.isoformat()
        await db.commit()
        logger.info(f"Admin {admin.username} blocked user {user.username} for {block_req.lock_duration_days} days until {lock_until}")
        return {"message": f"Użytkownik {user.username} zablokowany na {block_req.lock_duration_days} dni (do {lock_until.strftime('%Y-%m-%d %H:%M')})"}


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Unblock a user account."""
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    user.locked_until = None
    user.failed_login_attempts = 0
    
    await db.commit()
    logger.info(f"Admin {admin.username} unblocked user {user.username}")
    
    return {"message": f"User {user.username} unblocked successfully"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    reset_req: ResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reset a user's password."""
    from app.core.security import get_password_hash
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(reset_req.new_password)
    await db.commit()
    
    logger.info(f"Admin {admin.username} reset password for user {user.username}")
    
    return {"message": f"Password reset successfully for user {user.username}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user account completely."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete related records to prevent IntegrityError
    # Delete TransactionHistory first because it references Order
    await db.execute(TransactionHistory.__table__.delete().where(TransactionHistory.user_id == user_id))
    await db.execute(Order.__table__.delete().where(Order.user_id == user_id))
    await db.execute(Wallet.__table__.delete().where(Wallet.user_id == user_id))
    
    await db.delete(user)
    await db.commit()
    logger.info(f"Admin {admin.username} deleted user {user.username} and all related records")
    
    return {"message": f"User {user.username} deleted successfully"}
@router.get("/transactions", response_model=List[TransactionResponse])
async def list_all_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all transactions in the system with user information."""
    query = select(TransactionHistory, User.username).join(User, TransactionHistory.user_id == User.id)
    
    if user_id:
        query = query.filter(TransactionHistory.user_id == user_id)
    
    query = query.order_by(desc(TransactionHistory.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    transactions = []
    for tx, username in rows:
        transactions.append({
            "id": tx.id,
            "user_id": tx.user_id,
            "username": username,
            "order_id": tx.order_id,
            "type": tx.type,
            "amount": tx.amount,
            "asset": tx.asset,
            "price": tx.price,
            "fee": tx.fee,
            "status": tx.status,
            "log_message": tx.log_message,
            "created_at": tx.created_at.isoformat() if tx.created_at else ""
        })
    
    return transactions


@router.get("/orders")
async def list_all_orders(
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all orders in the system."""
    query = select(Order, User.username).join(User, Order.user_id == User.id)
    
    if status:
        query = query.filter(Order.status == status)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    
    query = query.order_by(desc(Order.created_at))
    result = await db.execute(query)
    rows = result.all()
    
    orders = []
    for order, username in rows:
        orders.append({
            "id": order.id,
            "user_id": order.user_id,
            "username": username,
            "symbol": order.symbol,
            "order_type": order.order_type,
            "side": order.side,
            "amount": order.amount,
            "target_price": order.target_price,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else ""
        })
    
    return orders


@router.put("/config")
async def update_system_config(
    config_req: UpdateConfigRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update system configuration."""
    updates = []
    
    if config_req.trading_fee_rate is not None:
        if config_req.trading_fee_rate < 0 or config_req.trading_fee_rate > 1:
            raise HTTPException(status_code=400, detail="Trading fee rate must be between 0 and 1")
        settings.TRADING_FEE_RATE = config_req.trading_fee_rate
        updates.append(f"trading_fee_rate={config_req.trading_fee_rate}")
    
    if config_req.tracked_symbols is not None:
        settings.TRACKED_SYMBOLS = config_req.tracked_symbols
        updates.append(f"tracked_symbols={config_req.tracked_symbols}")
    
    logger.info(f"Admin {admin.username} updated system config: {', '.join(updates)}")
    
    return {"message": f"Configuration updated: {', '.join(updates)}"}


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics."""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one()
    
    # Active users
    active_users_result = await db.execute(select(func.count(User.id)).filter(User.is_active == True))
    active_users = active_users_result.scalar_one()
    
    # Total transactions
    total_tx_result = await db.execute(select(func.count(TransactionHistory.id)))
    total_transactions = total_tx_result.scalar_one()
    
    # Total orders by status
    orders_result = await db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    )
    orders_by_status = {status: count for status, count in orders_result.all()}
    
    # Calculate wallet values split by SPOT and FUTURES
    spot_wallet_value = 0.0
    futures_wallet_value = 0.0
    from app.services.market_data import BinanceClient, market_data_service
    prices = await market_data_service.get_all_prices()
    
    # Find live users (with configured Binance keys)
    live_users_result = await db.execute(
        select(User).where(
            User.binance_api_key.is_not(None),
            User.binance_api_key != '',
            ~User.binance_api_key.like('%WKLEJ%')
        )
    )
    live_users = live_users_result.scalars().all()
    live_user_ids = {u.id for u in live_users}
    
    # For LIVE users: try Binance API (already returns SPOT/FUTURES split)
    for l_user in live_users:
        binance_ok = False
        try:
            client = BinanceClient()
            client.api_key = l_user.binance_api_key
            client.api_secret = l_user.binance_secret_key
            client.headers = {"X-MBX-APIKEY": l_user.binance_api_key}
            balances = await client.get_account_balance()
            
            for wallet_type, assets in balances.items():
                for asset, data in assets.items():
                    balance = data.get("total", 0.0)
                    if balance > 0:
                        usd_value = 0.0
                        if asset in ("USDT", "USDC"):
                            usd_value = balance
                        elif f"{asset}USDT" in prices:
                            usd_value = balance * prices[f"{asset}USDT"]
                        
                        if wallet_type == "SPOT":
                            spot_wallet_value += usd_value
                        else:
                            futures_wallet_value += usd_value
            binance_ok = True
        except Exception as e:
            logger.warning(f"Failed to fetch Binance balance for stats (User {l_user.username}): {e}")
        
        # Fallback to local DB if Binance API failed
        if not binance_ok:
            user_wallets_result = await db.execute(
                select(Wallet).where(Wallet.user_id == l_user.id)
            )
            user_wallets = user_wallets_result.scalars().all()
            for w in user_wallets:
                total_balance = w.balance + w.locked_balance
                if total_balance > 0:
                    usd_value = 0.0
                    if w.asset_symbol in ("USDT", "USDC"):
                        usd_value = total_balance
                    elif f"{w.asset_symbol}USDT" in prices:
                        usd_value = total_balance * prices[f"{w.asset_symbol}USDT"]
                    
                    if w.wallet_type == "FUTURES":
                        futures_wallet_value += usd_value
                    else:
                        spot_wallet_value += usd_value
    
    # For non-LIVE users: use local DB with wallet_type field
    if live_user_ids:
        sim_wallets_result = await db.execute(
            select(Wallet).where(~Wallet.user_id.in_(live_user_ids))
        )
    else:
        sim_wallets_result = await db.execute(select(Wallet))
    sim_wallets = sim_wallets_result.scalars().all()
    
    for w in sim_wallets:
        total_balance = w.balance + w.locked_balance
        if total_balance > 0:
            usd_value = 0.0
            if w.asset_symbol in ("USDT", "USDC"):
                usd_value = total_balance
            elif f"{w.asset_symbol}USDT" in prices:
                usd_value = total_balance * prices[f"{w.asset_symbol}USDT"]
            
            if w.wallet_type == "FUTURES":
                futures_wallet_value += usd_value
            else:
                spot_wallet_value += usd_value
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_transactions": total_transactions,
        "orders_by_status": orders_by_status,
        "spot_wallet_value": spot_wallet_value,
        "futures_wallet_value": futures_wallet_value,
        "total_wallet_value": spot_wallet_value + futures_wallet_value
    }
