from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True, nullable=False) # e.g. BTCUSDT
    order_type = Column(String, nullable=False) # 'STOP_LOSS' lub 'TAKE_PROFIT'
    side = Column(String, default="SELL") # 'BUY' or 'SELL' - akcja po aktywacji
    amount = Column(Float, nullable=False) # Ilość aktywa
    target_price = Column(Float, nullable=False) # Próg cenowy aktywacji
    leverage = Column(Integer, default=1) # Dźwignia użyta przy otwarciu
    group_id = Column(String(50), index=True, nullable=True) # Grupa dla OCO (TP/SL)
    status = Column(String, default="ACTIVE") # 'ACTIVE', 'COMPLETED', 'CANCELLED', 'FAILED'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
