from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True) # opcjonalnie
    type = Column(String, nullable=False) # 'DEPOSIT', 'WITHDRAWAL', 'SELL', 'BUY', 'FEE'
    amount = Column(Float, nullable=False)
    asset = Column(String, nullable=False)
    price = Column(Float, nullable=True) # Cena egzekucji np. 60000.0 (dla transakcji giełdowych)
    fee = Column(Float, default=0.0)
    status = Column(String, default="COMPLETED") # 'COMPLETED', 'FAILED'
    log_message = Column(String, nullable=True) # Powód np. "Transakcja Stop-Loss wykonana", "Brak srodkow"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
