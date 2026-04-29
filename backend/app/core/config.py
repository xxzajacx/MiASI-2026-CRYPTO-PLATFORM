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
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    
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

settings = Settings()
