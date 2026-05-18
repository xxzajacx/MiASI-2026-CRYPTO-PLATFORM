"""Tests for portfolio endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.wallet import Wallet
from app.core.security import get_password_hash, create_access_token

API_URL = "http://test"


@pytest.fixture
async def portfolio_user(db_session: AsyncSession):
    """Create user with wallet."""
    user = User(
        username="portfoliouser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Portfolio",
        last_name="User",
        birth_date="2000-01-01"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create wallets
    btc_wallet = Wallet(user_id=user.id, asset_symbol="BTC", balance=1.5, locked_balance=0.5)
    usdt_wallet = Wallet(user_id=user.id, asset_symbol="USDT", balance=10000.0, locked_balance=0.0)
    db_session.add_all([btc_wallet, usdt_wallet])
    await db_session.commit()
    
    token = create_access_token({"sub": "portfoliouser"})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest.mark.asyncio
async def test_get_portfolio(client: AsyncClient, db_session: AsyncSession, portfolio_user):
    """Test getting user portfolio."""
    headers, user_id = portfolio_user
    
    response = await client.get("/api/portfolio/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # BTC and USDT wallets
    
    # Find BTC wallet
    btc = next(w for w in data if w["asset_symbol"] == "BTC")
    assert btc["balance"] == 1.5
    assert btc["locked_balance"] == 0.5


@pytest.mark.asyncio
async def test_get_portfolio_empty(client: AsyncClient, db_session: AsyncSession):
    """Test getting portfolio for user with no wallets."""
    user = User(
        username="noportfolio",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="No",
        last_name="Portfolio",
        birth_date="2000-01-01"
    )
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token({"sub": "noportfolio"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/portfolio/", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_deposit_funds(client: AsyncClient, db_session: AsyncSession, portfolio_user):
    """Test depositing funds to wallet."""
    headers, user_id = portfolio_user
    
    response = await client.post("/api/portfolio/deposit", json={
        "asset_symbol": "USDT",
        "amount": 5000.0
    }, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "5000.0 USDT" in data["message"]
    
    # Verify wallet updated
    result = await db_session.execute(
        select(Wallet).filter(Wallet.user_id == user_id, Wallet.asset_symbol == "USDT")
    )
    wallet = result.scalars().first()
    assert wallet.balance == 15000.0  # 10000 + 5000


@pytest.mark.asyncio
async def test_deposit_creates_wallet_if_not_exists(client: AsyncClient, db_session: AsyncSession):
    """Test deposit creates new wallet if it doesn't exist."""
    user = User(
        username="newdeposit",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="New",
        last_name="Deposit",
        birth_date="2000-01-01"
    )
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token({"sub": "newdeposit"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post("/api/portfolio/deposit", json={
        "asset_symbol": "ETH",
        "amount": 10.0
    }, headers=headers)
    
    assert response.status_code == 200
    
    # Verify wallet created
    result = await db_session.execute(
        select(Wallet).filter(Wallet.user_id == user.id, Wallet.asset_symbol == "ETH")
    )
    wallet = result.scalars().first()
    assert wallet is not None
    assert wallet.balance == 10.0


@pytest.mark.asyncio
async def test_deposit_invalid_amount(client: AsyncClient, portfolio_user):
    """Test deposit with invalid amount fails."""
    headers, _ = portfolio_user
    
    response = await client.post("/api/portfolio/deposit", json={
        "asset_symbol": "USDT",
        "amount": -100.0
    }, headers=headers)
    
    assert response.status_code == 422  # Validation error
