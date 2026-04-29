from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import api_router
from .api.trading import router as trading_router
from .core.config import settings
from .core.database import engine, Base
import asyncio
from .services.market_data import market_data_service
from .services.order_engine import start_order_engine

# Ensure all SQLAlchemy models are registered
import app.models

app = FastAPI(title="Giełda API", description="Cryptocurrency Investment Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(trading_router, prefix="/api/trading")

@app.on_event("startup")
async def startup_event():
    """Initialize database schemas and start background services."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize background market data and order engine tasks
    asyncio.create_task(market_data_service.start_fetching_task())
    asyncio.create_task(start_order_engine())

@app.get("/")
def root():
    return {"message": "Welcome to Giełda API"}
