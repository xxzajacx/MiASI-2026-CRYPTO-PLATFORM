"""Tests for admin endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.order import Order
from app.models.wallet import Wallet
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create admin user."""
    admin = User(
        username="admin",
        hashed_password=get_password_hash("AdminPass123!"),
        first_name="Admin",
        last_name="User",
        birth_date="2000-01-01",
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    
    token = create_access_token({"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    return headers, admin.id


@pytest.fixture
async def regular_user(db_session: AsyncSession):
    """Create regular user."""
    user = User(
        username="regular",
        hashed_password=get_password_hash("UserPass123!"),
        first_name="Regular",
        last_name="User",
        birth_date="2000-01-01",
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    return user.id


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, db_session: AsyncSession, admin_user):
    """Test admin can list all users."""
    headers, _ = admin_user
    
    response = await client.get("/api/admin/users", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_users_non_admin_forbidden(client: AsyncClient, db_session: AsyncSession, regular_user):
    """Test non-admin cannot access admin endpoints."""
    token = create_access_token({"sub": "regular"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/admin/users", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_details(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can get user details."""
    headers, _ = admin_user
    
    response = await client.get(f"/api/admin/users/{regular_user}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "regular"
    assert "wallets" in data
    assert "active_orders_count" in data


@pytest.mark.asyncio
async def test_block_user(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can block a user."""
    headers, admin_id = admin_user
    
    response = await client.post(
        f"/api/admin/users/{regular_user}/block",
        json={"lock_duration_minutes": 60},
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify user is blocked
    result = await db_session.execute(select(User).filter(User.id == regular_user))
    user = result.scalars().first()
    assert user.is_active is False
    assert user.locked_until is not None


@pytest.mark.asyncio
async def test_unblock_user(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can unblock a user."""
    headers, _ = admin_user
    
    # First block the user
    result = await db_session.execute(select(User).filter(User.id == regular_user))
    user = result.scalars().first()
    user.is_active = False
    user.locked_until = "2026-01-01T00:00:00"
    user.failed_login_attempts = 5
    await db_session.commit()
    
    # Unblock
    response = await client.post(f"/api/admin/users/{regular_user}/unblock", headers=headers)
    assert response.status_code == 200
    
    # Verify
    await db_session.refresh(user)
    assert user.is_active is True
    assert user.locked_until is None
    assert user.failed_login_attempts == 0


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can reset user password."""
    headers, _ = admin_user
    
    response = await client.post(
        f"/api/admin/users/{regular_user}/reset-password",
        json={"new_password": "NewPass123!"},
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify password changed (login with new password)
    from app.core.security import verify_password
    await db_session.refresh(regular_user)
    result = await db_session.execute(select(User).filter(User.id == regular_user))
    user = result.scalars().first()
    assert verify_password("NewPass123!", user.hashed_password)


@pytest.mark.asyncio
async def test_list_all_transactions(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can list all transactions."""
    headers, _ = admin_user
    
    response = await client.get("/api/admin/transactions", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_all_orders(client: AsyncClient, db_session: AsyncSession, admin_user, regular_user):
    """Test admin can list all orders."""
    headers, _ = admin_user
    
    response = await client.get("/api/admin/orders", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_system_stats(client: AsyncClient, db_session: AsyncSession, admin_user):
    """Test admin can get system statistics."""
    headers, _ = admin_user
    
    response = await client.get("/api/admin/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "total_transactions" in data


@pytest.mark.asyncio
async def test_admin_cannot_block_self(client: AsyncClient, db_session: AsyncSession, admin_user):
    """Test admin cannot block their own account."""
    headers, admin_id = admin_user
    
    response = await client.post(
        f"/api/admin/users/{admin_id}/block",
        json={"lock_duration_minutes": 60},
        headers=headers
    )
    assert response.status_code == 400
