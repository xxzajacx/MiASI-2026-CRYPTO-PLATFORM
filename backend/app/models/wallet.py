from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    asset_symbol = Column(String, index=True, nullable=False) # np. 'PLN', 'BTC', 'ETH'
    balance = Column(Float, default=0.0)
    locked_balance = Column(Float, default=0.0) # Zablokowane środki na poczet zleceń
