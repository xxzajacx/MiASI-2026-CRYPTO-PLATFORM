"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date, datetime, timedelta
from app.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token
import time


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful user registration."""
    response = await client.post("/api/auth/register-init", json={
        "username": "newuser",
        "password": "TestPass123!",
        "first_name": "John",
        "last_name": "Doe",
        "birth_date": "2000-01-01"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "totp_secret" in data
    
    # Verify user was created in database
    result = await db_session.execute(select(User).filter(User.username == "newuser"))
    user = result.scalars().first()
    assert user is not None
    assert user.first_name == "John"
    

@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    """Test registration with duplicate username fails."""
    # Create first user
    user = User(
        username="existinguser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Jane",
        last_name="Doe",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to register with same username
    response = await client.post("/api/auth/register-init", json={
        "username": "existinguser",
        "password": "TestPass123!",
        "first_name": "John",
        "last_name": "Doe",
        "birth_date": "2000-01-01"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()
    

@pytest.mark.asyncio
async def test_register_user_invalid_password(client: AsyncClient):
    """Test registration with weak password fails."""
    response = await client.post("/api/auth/register-init", json={
        "username": "weakuser",
        "password": "123",  # Too short and simple
        "first_name": "John",
        "last_name": "Doe",
        "birth_date": "2000-01-01"
    })
    assert response.status_code == 400  # Validation error


@pytest.mark.asyncio
async def test_register_user_underage(client: AsyncClient):
    """Test registration with age < 18 fails."""
    underage_date = (datetime.now() - timedelta(days=365*17)).strftime("%Y-%m-%d")
    
    response = await client.post("/api/auth/register-init", json={
        "username": "younguser",
        "password": "TestPass123!",
        "first_name": "Young",
        "last_name": "User",
        "birth_date": underage_date
    })
    assert response.status_code == 400
    assert "18 lat" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login returns temporary token."""
    # Create user
    user = User(
        username="loginuser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Test",
        last_name="User",
        birth_date=date(2000, 1, 1),
        totp_secret="JBSWY3DPEHPK3PXP"
    )
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/auth/login", data={
        "username": "loginuser",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["is_temp"] is True


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """Test login with wrong password fails."""
    user = User(
        username="loginuser2",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Test",
        last_name="User",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/auth/login", data={
        "username": "loginuser2",
        "password": "WrongPass123!"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_account_lockout(client: AsyncClient, db_session: AsyncSession):
    """Test account locks after 5 failed attempts."""
    user = User(
        username="lockoutuser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Test",
        last_name="User",
        birth_date=date(2000, 1, 1),
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    
    # Attempt 5 failed logins
    for i in range(5):
        response = await client.post("/api/auth/login", data={
            "username": "lockoutuser",
            "password": "WrongPass!"
        })
    
    # 6th attempt should fail with lockout
    response = await client.post("/api/auth/login", data={
        "username": "lockoutuser",
        "password": "TestPass123!"
    })
    assert response.status_code == 403
    assert "zablokowane" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_2fa_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful 2FA verification."""
    import pyotp
    totp_secret = pyotp.random_base32()
    user = User(
        username="totpuser",
        hashed_password=get_password_hash("TestPass123!"),
        totp_secret=totp_secret,
        first_name="Test",
        last_name="User",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    # Get temp token first
    response = await client.post("/api/auth/login", data={
        "username": "totpuser",
        "password": "TestPass123!"
    })
    temp_token = response.json()["access_token"]
    
    # Verify with correct TOTP
    totp = pyotp.TOTP(totp_secret)
    response = await client.post(
        "/api/auth/verify-2fa",
        headers={"Authorization": f"Bearer {temp_token}"},
        json={"code": totp.now()}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_temp"] is False
    assert "access_token" in data


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db_session: AsyncSession):
    """Test getting current user info."""
    # Create user and get token
    from app.core.security import create_access_token
    user = User(
        username="meuser",
        hashed_password=get_password_hash("TestPass123!"),
        first_name="Me",
        last_name="User",
        birth_date=date(2000, 1, 1)
    )
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token({"sub": "meuser"})
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"
