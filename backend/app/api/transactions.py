from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.transaction import TransactionHistory
from app.models.user import User

router = APIRouter()

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    order_id: Optional[int] = None
    type: str
    amount: float
    asset: str
    price: Optional[float] = None
    fee: float
    status: str
    log_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    limit: int
    offset: int

@router.get("/", response_model=PaginatedTransactionResponse, summary="Get user transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get total count of user's transactions
    total_result = await db.execute(
        select(func.count(TransactionHistory.id)).filter(TransactionHistory.user_id == current_user.id)
    )
    total = total_result.scalar_one()

    # Get paginated transaction items, ordered by most recent first
    result = await db.execute(
        select(TransactionHistory)
        .filter(TransactionHistory.user_id == current_user.id)
        .order_by(TransactionHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()
    
    return {
        "items": transactions,
        "total": total,
        "limit": limit,
        "offset": offset
    }
