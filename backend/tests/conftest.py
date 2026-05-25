import sys
import os
os.environ["TESTING"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.core.database import Base, get_db, AsyncSessionLocal
from app.core.security import get_password_hash, create_access_token, generate_totp_secret
from app.models.user import User

# Use file-based SQLite for tests to persist tables
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine_test = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_test, class_=AsyncSession, expire_on_commit=False
)

# Create tables for every test to ensure database isolation
@pytest_asyncio.fixture(autouse=True)
async def create_test_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        if os.path.exists("./test.db"):
            os.remove("./test.db")
    except Exception:
        pass

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

fastapi_app.dependency_overrides[get_db] = override_get_db

# Override AsyncSessionLocal in app.core.database so order_engine uses it
import app.core.database as app_core_db
app_core_db.AsyncSessionLocal = TestingSessionLocal

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def create_user(db_session):
    """Create a test user and return headers with auth token and user_id."""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Test",
        last_name="User",
        birth_date=date(2000, 1, 1),
        totp_secret=generate_totp_secret()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create access token
    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest_asyncio.fixture
async def portfolio_user(db_session):
    """Create a test user with wallet for portfolio tests."""
    from app.models.wallet import Wallet
    
    user = User(
        username="portfolio_user",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Portfolio",
        last_name="User",
        birth_date=date(2000, 1, 1),
        totp_secret=generate_totp_secret()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Add wallet
    wallet = Wallet(user_id=user.id, asset_symbol="USDT", balance=10000.0, locked_balance=0.0)
    db_session.add(wallet)
    await db_session.commit()
    
    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest_asyncio.fixture
async def trading_user(db_session):
    """Create a test user with wallet for trading tests."""
    from app.models.wallet import Wallet
    
    user = User(
        username="trader",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Trader",
        last_name="User",
        birth_date=date(2000, 1, 1),
        totp_secret=generate_totp_secret()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Add wallets
    wallet_usdt = Wallet(user_id=user.id, asset_symbol="USDT", balance=50000.0, locked_balance=0.0)
    wallet_btc = Wallet(user_id=user.id, asset_symbol="BTC", balance=1.0, locked_balance=0.0)
    db_session.add_all([wallet_usdt, wallet_btc])
    await db_session.commit()
    
    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id


@pytest_asyncio.fixture
async def tx_user(db_session):
    """Create a test user with transaction history."""
    from app.models.wallet import Wallet
    from app.models.transaction import TransactionHistory
    
    user = User(
        username="tx_user",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Tx",
        last_name="User",
        birth_date=date(2000, 1, 1),
        totp_secret=generate_totp_secret()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Add wallet and transaction
    wallet = Wallet(user_id=user.id, asset_symbol="USDT", balance=10000.0, locked_balance=0.0)
    tx = TransactionHistory(
        user_id=user.id,
        order_id=None,
        type="BUY",
        amount=0.5,
        asset="BTC",
        price=50000.0,
        fee=25.0,
        status="COMPLETED"
    )
    db_session.add_all([wallet, tx])
    await db_session.commit()
    
    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user.id
