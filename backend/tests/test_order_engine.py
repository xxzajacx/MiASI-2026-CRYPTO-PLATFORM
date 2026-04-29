import pytest
from sqlalchemy.future import select
from app.models.order import Order
from app.models.wallet import Wallet
from app.models.user import User
from app.services.order_engine import process_orders
from app.services.market_data import market_data_service
import app.services.order_engine as engine_module

# Override AsyncSessionLocal inside process_orders for testing
from tests.conftest import TestingSessionLocal
engine_module.AsyncSessionLocal = TestingSessionLocal

@pytest.mark.asyncio
async def test_stop_loss_execution_success(db_session):
    # Setup test user and wallet
    user = User(username="testuser", hashed_password="hashed_pw")
    db_session.add(user)
    await db_session.commit()
    
    # Przeznaczamy 2 zablokowane BTC na pokrycie SL Stop-Loss
    wallet_btc = Wallet(user_id=user.id, asset_symbol="BTC", balance=0.0, locked_balance=2.0)
    db_session.add(wallet_btc)
    
    # Tworzymy Order na sprzedaż 1 BTC jesli cena spadnie ponizej 50000
    order = Order(user_id=user.id, symbol="BTCUSDT", order_type="STOP_LOSS", amount=1.0, target_price=50000.0)
    db_session.add(order)
    await db_session.commit()

    # Mock market prices -> cena rynkowa to 49000 (spadek ponizej 50000 -> powinno wyzwolić)
    market_data_service.prices = {"BTCUSDT": 49000.0}

    # Execute
    await process_orders()

    # Verify order completion and fiat wallet updates
    await db_session.refresh(order)
    assert order.status == "COMPLETED"

    res_wallet = await db_session.execute(select(Wallet).filter(Wallet.user_id == user.id, Wallet.asset_symbol == "USDT"))
    wallet_fiat = res_wallet.scalars().first()
    
    # 1.0 BTC * 49000 = 49000. - 0.5% fee(245) = 48755 USDT
    assert wallet_fiat is not None
    assert wallet_fiat.balance == 48755.0

@pytest.mark.asyncio
async def test_take_profit_execution_success(db_session):
    user = User(username="tp_user", hashed_password="123")
    db_session.add(user)
    await db_session.commit()
    
    wallet_btc = Wallet(user_id=user.id, asset_symbol="BTC", balance=0.0, locked_balance=0.5)
    db_session.add(wallet_btc)
    
    order = Order(user_id=user.id, symbol="BTCUSDT", order_type="TAKE_PROFIT", amount=0.5, target_price=60000.0)
    db_session.add(order)
    await db_session.commit()

    # Cena 61000 >= 60000 wiec powinno zadziałać Take-Profit
    market_data_service.prices = {"BTCUSDT": 61000.0}
    await process_orders()

    await db_session.refresh(order)
    assert order.status == "COMPLETED"

    res_wallet = await db_session.execute(select(Wallet).filter(Wallet.user_id == user.id, Wallet.asset_symbol == "BTC"))
    wallet_crypto = res_wallet.scalars().first()
    # Pieniądze powinny zostać ściągnięte z locked_balance
    assert wallet_crypto.locked_balance == 0.0

@pytest.mark.asyncio
async def test_order_ignored_when_conditions_not_met(db_session):
    user = User(username="user3", hashed_password="pwd")
    db_session.add(user)
    await db_session.commit()
    
    order = Order(user_id=user.id, symbol="BTCUSDT", order_type="STOP_LOSS", amount=1.0, target_price=40000.0)
    db_session.add(order)
    await db_session.commit()

    # Cena wynosi 41000 (wyzej niz SL), zlecenie powinno być zignorowane
    market_data_service.prices = {"BTCUSDT": 41000.0}
    await process_orders()

    await db_session.refresh(order)
    assert order.status == "ACTIVE" # Nie odpalone

@pytest.mark.asyncio
async def test_order_fails_on_insufficient_wallet(db_session):
    user = User(username="user4", hashed_password="pwd")
    db_session.add(user)
    await db_session.commit()
    
    # Tylko 0.1 w portfelu lockowanym a order zakłada sprzedaż 1.0!
    wallet_btc = Wallet(user_id=user.id, asset_symbol="BTC", balance=0.0, locked_balance=0.1)
    db_session.add(wallet_btc)
    
    order = Order(user_id=user.id, symbol="BTCUSDT", order_type="STOP_LOSS", amount=1.0, target_price=40000.0)
    db_session.add(order)
    await db_session.commit()

    market_data_service.prices = {"BTCUSDT": 39000.0}
    await process_orders()

    await db_session.refresh(order)
    assert order.status == "FAILED"
