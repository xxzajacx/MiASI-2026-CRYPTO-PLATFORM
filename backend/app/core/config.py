import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/gielda"
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_temporary_key_replace_me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174")
    
    # Binance Demo Config
    BINANCE_MODE: str = os.getenv("BINANCE_MODE", "demo")
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_BASE_URL: str = os.getenv("BINANCE_BASE_URL", "https://demo-api.binance.com")
    BINANCE_WS_URL: str = os.getenv("BINANCE_WS_URL", "wss://demo-stream.binance.com")
    
    # Trading Config
    TRACKED_SYMBOLS: str = os.getenv("TRACKED_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT")
    TRADING_FEE_RATE: float = float(os.getenv("TRADING_FEE_RATE", "0.001"))
    
    # Rate Limit
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "1200"))

    # Email (SMTP) – used for transaction confirmation on high-value operations
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@gielda.app")

    # Threshold (in USDT) above which email confirmation is required for trades
    EMAIL_CONFIRM_THRESHOLD: float = float(os.getenv("EMAIL_CONFIRM_THRESHOLD", "1000"))

settings = Settings()
