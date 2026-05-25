"""Tests for trading endpoints."""
import pytest
from datetime import date
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.wallet import Wallet
from app.core.security import get_password_hash, create_access_token

API_URL = "http://test"


@pytest.fixture
async def trading_user(db_session: AsyncSession):
    """Create user and return auth headers."""
    user = User(
        username="trader",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Trade",
        last_name="User",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token({"sub": "trader"})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest.mark.asyncio
async def test_market_buy_success(client: AsyncClient, db_session: AsyncSession, trading_user):
    """Test market buy order."""
    headers, user_id = trading_user
    
    with patch('app.services.market_data.BinanceClient.execute_trade') as mock:
        mock.return_value = {
            "order_id": 12345,
            "symbol": "BTCUSDT",
            "executed_qty": 0.1,
            "cummulative_quote_qty": 5000.0,
            "fills": [{"qty": "0.1", "price": "50000", "commission": "0.05"}]
        }
        
        response = await client.post("/api/trading/buy", json={
            "symbol": "BTCUSDT",
            "quantity": 0.1
        }, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["executed_qty"] == 0.1


@pytest.mark.asyncio
async def test_market_sell_success(client: AsyncClient, db_session: AsyncSession, trading_user):
    """Test market sell order."""
    headers, user_id = trading_user
    
    with patch('app.services.market_data.BinanceClient.execute_trade') as mock:
        mock.return_value = {
            "orderId": 12346,
            "symbol": "BTCUSDT",
            "fills": [
                {"qty": "0.5", "price": "51000", "commission": "0.0255"}
            ]
        }
        
        response = await client.post("/api/trading/market-sell", json={
            "symbol": "BTCUSDT",
            "quantity": 0.5
        }, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_market_buy_invalid_symbol(client: AsyncClient, trading_user):
    """Test market buy with invalid symbol fails."""
    headers, _ = trading_user
    
    response = await client.post("/api/trading/buy", json={
        "symbol": "INVALID",
        "quantity": 0.1
    }, headers=headers)
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_market_buy_no_auth(client: AsyncClient):
    """Test market buy without auth fails."""
    response = await client.post("/api/trading/buy", json={
        "symbol": "BTCUSDT",
        "quantity": 0.1
    })
    
    assert response.status_code == 401
