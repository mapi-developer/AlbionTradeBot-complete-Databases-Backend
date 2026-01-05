from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List
from datetime import datetime
from database import Base

# ==========================================
# DATABASE 1: Trade Bot (Items)
# ==========================================

class ItemFast(Base):
    __tablename__ = "ItemFast"

    unique_name: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    
    # Prices
    price_black_market: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_caerleon: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_lymhurst: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_bridgewatch: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_fort_sterling: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_thetford: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_martlock: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_brecilien: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)

    # Timestamps
    black_market_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    caerleon_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lymhurst_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    bridgewatch_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fort_sterling_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thetford_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    martlock_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    brecilien_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ItemOrder(Base):
    __tablename__ = "ItemOrder"

    unique_name: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    
    # Prices
    price_black_market: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_caerleon: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_lymhurst: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_bridgewatch: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_fort_sterling: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_thetford: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_martlock: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)
    price_brecilien: Mapped[Optional[BigInteger]] = mapped_column(BigInteger)

    # Timestamps
    black_market_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    caerleon_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lymhurst_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    bridgewatch_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fort_sterling_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    thetford_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    martlock_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    brecilien_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ==========================================
# DATABASE 2: Crypto Backend (Users & Invoices)
# ==========================================

class User(Base):
    __tablename__ = "User"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    profile_picture: Mapped[Optional[str]] = mapped_column(String)
    google_id: Mapped[Optional[str]] = mapped_column(String)
    discord_id: Mapped[Optional[str]] = mapped_column(String)
    
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    subscribed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="user")


class Invoice(Base):
    __tablename__ = "Invoice"

    id: Mapped[BigInteger] = mapped_column(BigInteger, primary_key=True) # External Payment ID
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("User.id"), index=True)
    
    status: Mapped[str] = mapped_column(String) # waiting, finished, failed
    price_amount: Mapped[float] = mapped_column(Float)
    pay_currency: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="invoices")