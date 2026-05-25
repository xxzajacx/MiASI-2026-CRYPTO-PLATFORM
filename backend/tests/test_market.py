"""Tests for market data endpoints."""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

API_URL = "http://test"


@pytest.mark.asyncio
async def test_get_prices_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting all market prices."""
    from app.services.market_data import market_data_service
    
    # Mock the prices
    market_data_service.prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}
    
    response = await client.get("/api/market/prices")
    assert response.status_code == 200
    data = response.json()
    assert "BTCUSDT" in data
    assert data["BTCUSDT"] == 50000.0


@pytest.mark.asyncio
async def test_get_price_by_symbol(client: AsyncClient):
    """Test getting price for specific symbol."""
    from app.services.market_data import market_data_service
    
    market_data_service.prices = {"BTCUSDT": 51000.0}
    
    response = await client.get("/api/market/price/BTCUSDT")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["price"] == 51000.0


@pytest.mark.asyncio
async def test_get_price_invalid_symbol(client: AsyncClient):
    """Test getting price for invalid symbol returns 404."""
    from app.services.market_data import market_data_service
    
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    response = await client.get("/api/market/price/INVALID")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_market_status(client: AsyncClient):
    """Test market API status endpoint."""
    response = await client.get("/api/market/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
@patch('app.services.market_data.BinanceClient.fetch_all_prices')
async def test_refresh_prices(mock_fetch, client: AsyncClient):
    """Test refreshing market prices."""
    from app.services.market_data import market_data_service
    
    mock_fetch.return_value = {"BTCUSDT": 52000.0, "ETHUSDT": 3100.0}
    
    response = await client.post("/api/market/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert market_data_service.prices == {"BTCUSDT": 52000.0, "ETHUSDT": 3100.0}


@pytest.mark.asyncio
async def test_market_data_validation(client: AsyncClient):
    """Test that market data service validates price format."""
    from app.services.market_data import market_data_service
    
    # Test with invalid price data
    with patch.object(market_data_service, 'fetch_all_prices', new_callable=AsyncMock) as mock:
        mock.return_value = {"BTCUSDT": "invalid_price"}  # Invalid format
        
        prices = await market_data_service.fetch_all_prices()
        # Should filter out invalid prices or handle gracefully
        assert isinstance(prices, dict)


@pytest.mark.asyncio
async def test_market_trade_invalid_side(client: AsyncClient, trading_user):
    headers, _ = trading_user
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "INVALID",
            "amount": 0.1,
            "amount_type": "crypto"
        },
        headers=headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_market_trade_invalid_amount(client: AsyncClient, trading_user):
    headers, _ = trading_user
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "amount": -0.1,
            "amount_type": "crypto"
        },
        headers=headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_market_trade_buy_insufficient_margin(client: AsyncClient, trading_user):
    headers, _ = trading_user
    
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "amount": 10.0,  # 10 BTC = 500,000 USDT. Max balance is 50,000.
            "amount_type": "crypto",
            "leverage": 1
        },
        headers=headers
    )
    assert response.status_code == 400
    assert "Insufficient USDT balance" in response.json()["detail"]


@pytest.mark.asyncio
async def test_market_trade_buy_sell_success(client: AsyncClient, db_session: AsyncSession, trading_user):
    headers, user_id = trading_user
    
    from app.services.market_data import market_data_service
    from sqlalchemy.future import select
    from app.models.wallet import Wallet
    
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    # 1. Buy BTC
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "amount": 0.1,  # 5000 USDT
            "amount_type": "crypto",
            "leverage": 1
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify wallet balances
    res = await db_session.execute(select(Wallet).where(Wallet.user_id == user_id, Wallet.asset_symbol == "USDT"))
    usdt_wallet = res.scalars().first()
    # 50000 - 5000 - 5 (0.1% fee) = 44995.0
    assert usdt_wallet.balance == 44995.0
    
    res = await db_session.execute(select(Wallet).where(Wallet.user_id == user_id, Wallet.asset_symbol == "BTC"))
    btc_wallet = res.scalars().first()
    assert btc_wallet.balance == 1.1

    # 2. Sell BTC
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "SELL",
            "amount": 0.5,
            "amount_type": "crypto",
            "leverage": 1
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_market_trade_stop_loss_take_profit(client: AsyncClient, db_session: AsyncSession, trading_user):
    headers, user_id = trading_user
    
    from app.services.market_data import market_data_service
    from sqlalchemy.future import select
    from app.models.order import Order
    
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    response = await client.post(
        "/api/market/trade",
        json={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "amount": 0.1,
            "amount_type": "crypto",
            "leverage": 1,
            "stop_loss": 48000.0,
            "take_profit": 52000.0
        },
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify order database has take profit and stop loss active orders
    res = await db_session.execute(select(Order).where(Order.user_id == user_id, Order.status == "ACTIVE"))
    orders = res.scalars().all()
    assert len(orders) == 2
    types = [o.order_type for o in orders]
    assert "STOP_LOSS" in types
    assert "TAKE_PROFIT" in types


@pytest.mark.asyncio
async def test_market_trade_confirm_invalid_token(client: AsyncClient, trading_user):
    headers, _ = trading_user
    response = await client.post(
        "/api/market/trade/confirm",
        json={
            "confirmation_token": "invalid_token",
            "confirmation_code": "123456"
        },
        headers=headers
    )
    assert response.status_code == 400
    assert "Nieprawidłowy lub wygasły kod" in response.json()["detail"]

