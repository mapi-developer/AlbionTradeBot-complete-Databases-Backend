from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List
from datetime import datetime
from database import Base

# ==========================================
# DATABASE 1: Trade Bot (Items & Prices)
# ==========================================

class Item(Base):
    __tablename__ = "Item"

    # The diagram shows unique_name has the Key icon (Primary Key)
    unique_name: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    
    # Prices (using BigInteger for 'bigint')
    price_black_market: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_caerleon: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_lymhurst: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_bridgewatch: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_fort_sterling: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_thetford: Mapped[Optional[int]] = mapped_column(BigInteger)
    price_martlock: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Timestamps
    black_market_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    caerleon_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lymhurst_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    bridgewatch_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fort_sterling_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thetford_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    martlock_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    avg_price_data = relationship("AvgPrice", uselist=False, back_populates="item_data")


class AvgPrice(Base):
    __tablename__ = "AvgPrice"

    # Diagram shows unique_name is PK here too, likely a 1:1 shared PK with Item
    unique_name: Mapped[str] = mapped_column(String, ForeignKey("Item.unique_name"), primary_key=True)
    
    # Day/Week/Month stats
    black_market_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    black_market_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    black_market_month: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    caerleon_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    caerleon_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    caerleon_month: Mapped[Optional[int]] = mapped_column(BigInteger)

    lymhurst_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    lymhurst_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    lymhurst_month: Mapped[Optional[int]] = mapped_column(BigInteger)

    bridgewatch_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    bridgewatch_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    bridgewatch_month: Mapped[Optional[int]] = mapped_column(BigInteger)

    fort_sterling_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    fort_sterling_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    fort_sterling_month: Mapped[Optional[int]] = mapped_column(BigInteger)

    thetford_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    thetford_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    thetford_month: Mapped[Optional[int]] = mapped_column(BigInteger)

    martlock_day: Mapped[Optional[int]] = mapped_column(BigInteger)
    martlock_week: Mapped[Optional[int]] = mapped_column(BigInteger)
    martlock_month: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    black_market_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    caerleon_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lymhurst_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    bridgewatch_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fort_sterling_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thetford_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    martlock_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    item_data = relationship("Item", back_populates="avg_price_data")


# ==========================================
# DATABASE 2: Crypto Backend (Users & Invoices)
# ==========================================

class User(Base):
    __tablename__ = "User"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String) # Hashed
    profile_picture: Mapped[Optional[str]] = mapped_column(String)
    google_id: Mapped[Optional[str]] = mapped_column(String)
    discord_id: Mapped[Optional[str]] = mapped_column(String)
    
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    subscribed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="user")


class Invoice(Base):
    __tablename__ = "Invoice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("User.id"), index=True)
    
    status: Mapped[str] = mapped_column(String)
    subscription_plan: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="invoices")


class Payment(Base):
    __tablename__ = "Payment"

    # ID from NOWPayments
    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True) 
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("User.id"), index=True)
    
    status: Mapped[str] = mapped_column(String) # waiting, finished, failed
    price_amount: Mapped[float] = mapped_column(Float)
    pay_currency: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User")