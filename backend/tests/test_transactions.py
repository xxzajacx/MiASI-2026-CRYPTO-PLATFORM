"""Tests for transaction history endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.transaction import TransactionHistory
from app.core.security import get_password_hash, create_access_token

API_URL = "http://test"


@pytest.fixture
async def tx_user(db_session: AsyncSession):
    """Create user with transactions."""
    user = User(
        username="txuser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Tx",
        last_name="User",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create some transactions
    tx1 = TransactionHistory(
        user_id=user.id,
        type="BUY",
        amount=0.5,
        asset="BTC",
        price=50000.0,
        fee=0.05,
        status="COMPLETED",
        log_message="Test buy"
    )
    tx2 = TransactionHistory(
        user_id=user.id,
        type="SELL",
        amount=0.3,
        asset="BTC",
        price=51000.0,
        fee=0.03,
        status="COMPLETED",
        log_message="Test sell"
    )
    db_session.add_all([tx1, tx2])
    await db_session.commit()
    
    token = create_access_token({"sub": "txuser"})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest.mark.asyncio
async def test_get_transactions(client: AsyncClient, tx_user):
    """Test getting user's transaction history."""
    headers, _ = tx_user
    
    response = await client.get("/api/transactions/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_transactions_pagination(client: AsyncClient, db_session: AsyncSession, tx_user):
    """Test transaction pagination."""
    headers, user_id = tx_user
    
    # Add more transactions
    for i in range(5):
        tx = TransactionHistory(
            user_id=user_id,
            type="BUY",
            amount=0.1,
            asset="ETH",
            price=3000.0,
            fee=0.01,
            status="COMPLETED",
            log_message=f"Test buy {i}"
        )
        db_session.add(tx)
    await db_session.commit()
    
    # Get first page
    response = await client.get("/api/transactions/?limit=3&offset=0", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 7  # 2 + 5
    
    # Get second page
    response = await client.get("/api/transactions/?limit=3&offset=3", headers=headers)
    data = response.json()
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_get_transactions_no_auth(client: AsyncClient):
    """Test getting transactions without auth fails."""
    response = await client.get("/api/transactions/")
    assert response.status_code == 401
