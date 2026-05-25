"""Tests for orders endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.order import Order
from app.models.wallet import Wallet
from app.core.security import get_password_hash, create_access_token

@pytest.mark.asyncio
async def test_create_stop_loss_order(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test creating a stop-loss order."""
    headers, user_id = create_user
    
    # Mock market price
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    # Create wallet with balance
    wallet = Wallet(user_id=user_id, asset_symbol="BTC", balance=1.0, locked_balance=0.0)
    db_session.add(wallet)
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "STOP_LOSS",
        "amount": 1.0,
        "target_price": 45000.0
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_type"] == "STOP_LOSS"
    assert data["status"] == "ACTIVE"
    
    # Verify assets were locked
    await db_session.refresh(wallet)
    assert wallet.locked_balance == 1.0
    assert wallet.balance == 0.0


@pytest.mark.asyncio
async def test_create_take_profit_order(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test creating a take-profit order."""
    headers, user_id = create_user
    
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    wallet = Wallet(user_id=user_id, asset_symbol="BTC", balance=0.5, locked_balance=0.0)
    db_session.add(wallet)
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "TAKE_PROFIT",
        "amount": 0.5,
        "target_price": 55000.0
    })
    
    assert response.status_code == 200
    assert response.json()["order_type"] == "TAKE_PROFIT"


@pytest.mark.asyncio
async def test_create_order_invalid_type(client: AsyncClient, create_user):
    """Test creating order with invalid type fails."""
    headers, _ = create_user
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "INVALID_TYPE",
        "amount": 1.0,
        "target_price": 45000.0,
    })
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_order_insufficient_balance(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test creating order with insufficient balance fails."""
    headers, user_id = create_user
    
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    # Only 0.1 BTC in wallet
    wallet = Wallet(user_id=user_id, asset_symbol="BTC", balance=0.1, locked_balance=0.0)
    db_session.add(wallet)
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "STOP_LOSS",
        "amount": 1.0,  # Trying to sell 1.0 with only 0.1
        "target_price": 45000.0,
    })
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_order_invalid_target_price_sl(client: AsyncClient, create_user):
    """Test creating SL order with target price >= current price fails."""
    headers, _ = create_user
    
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "STOP_LOSS",
        "amount": 1.0,
        "target_price": 51000.0  # SL must be lower than current
    })
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_order_invalid_target_price_tp(client: AsyncClient, create_user):
    """Test creating TP order with target price <= current price fails."""
    headers, _ = create_user
    
    from app.services.market_data import market_data_service
    market_data_service.prices = {"BTCUSDT": 50000.0}
    
    client.headers.update(headers)
    
    response = await client.post("/api/orders/", json={
        "symbol": "BTCUSDT",
        "order_type": "TAKE_PROFIT",
        "amount": 1.0,
        "target_price": 49000.0  # TP must be higher than current
    })
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_orders(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test getting user's orders."""
    headers, user_id = create_user
    
    # Create some orders
    order1 = Order(user_id=user_id, symbol="BTCUSDT", order_type="STOP_LOSS", 
                     amount=1.0, target_price=45000.0, status="ACTIVE")
    order2 = Order(user_id=user_id, symbol="ETHUSDT", order_type="TAKE_PROFIT", 
                     amount=2.0, target_price=3500.0, status="ACTIVE")
    db_session.add_all([order1, order2])
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.get("/api/orders/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_cancel_order(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test cancelling an active order."""
    headers, user_id = create_user
    
    order = Order(user_id=user_id, symbol="BTCUSDT", order_type="STOP_LOSS", 
                  amount=1.0, target_price=45000.0, status="ACTIVE")
    db_session.add(order)
    await db_session.commit()
    
    # Create wallet with locked balance
    wallet = Wallet(user_id=user_id, asset_symbol="BTC", balance=0.0, locked_balance=1.0)
    db_session.add(wallet)
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.delete(f"/api/orders/{order.id}")
    assert response.status_code == 200
    
    # Verify order cancelled and assets unlocked
    await db_session.refresh(order)
    await db_session.refresh(wallet)
    assert order.status == "CANCELLED"
    assert wallet.locked_balance == 0.0
    assert wallet.balance == 1.0


@pytest.mark.asyncio
async def test_cancel_completed_order_fails(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test cancelling a completed order fails."""
    headers, user_id = create_user
    
    order = Order(user_id=user_id, symbol="BTCUSDT", order_type="STOP_LOSS", 
                  amount=1.0, target_price=45000.0, status="COMPLETED")
    db_session.add(order)
    await db_session.commit()
    
    client.headers.update(headers)
    
    response = await client.delete(f"/api/orders/{order.id}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_other_user_order_fails(client: AsyncClient, db_session: AsyncSession, create_user):
    """Test user cannot cancel another user's order."""
    from app.core.security import create_access_token
    
    # Create two users
    user1 = User(username="user1", hashed_password=get_password_hash("TestPass123!"),
                   first_name="User", last_name="One", birth_date=date(2000, 1, 1))
    user2 = User(username="user2", hashed_password=get_password_hash("TestPass123!"),
                   first_name="User", last_name="Two", birth_date=date(2000, 1, 1))
    db_session.add_all([user1, user2])
    await db_session.commit()
    
    # Create order for user1
    order = Order(user_id=user1.id, symbol="BTCUSDT", order_type="STOP_LOSS", 
                   amount=1.0, target_price=45000.0, status="ACTIVE")
    db_session.add(order)
    await db_session.commit()
    
    # Try to cancel with user2's token
    token = create_access_token({"sub": "user2"})
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)
    
    response = await client.delete(f"/api/orders/{order.id}")
    assert response.status_code == 404  # Order not found (not owned by user)
