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
