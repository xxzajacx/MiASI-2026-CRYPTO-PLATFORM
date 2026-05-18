"""Models for user management."""
from sqlalchemy import Column, Integer, String, Boolean, Date
from app.core.database import Base

class User(Base):
    """User model representing registered users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)  # Email for transaction confirmations
    hashed_password = Column(String, nullable=False)
    totp_secret = Column(String, nullable=True)  # Wygenerowany klucz dla 2FA
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Rola administratora
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(String, nullable=True)  # Przechowuje datę blokady w formacie ISO
    first_name = Column(String, nullable=False, default="")
    last_name = Column(String, nullable=False, default="")
    birth_date = Column(Date, nullable=False)  # Format YYYY-MM-DD
    binance_api_key = Column(String, nullable=True)  # Per-user Binance API key
    binance_secret_key = Column(String, nullable=True)  # Per-user Binance secret key


