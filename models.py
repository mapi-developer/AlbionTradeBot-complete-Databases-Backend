from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import Base

# ==========================================
# DATABASE 1: Trade Bot (Items) - SHARED STRUCTURE
# ==========================================

class ItemBase:
    """
    Mixin class containing all shared columns for Item tables.
    """
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

# --- EU Tables ---
class ItemFastEU(Base, ItemBase):
    __tablename__ = "ItemFastEU"

class ItemOrderEU(Base, ItemBase):
    __tablename__ = "ItemOrderEU"

# --- US Tables ---
class ItemFastUS(Base, ItemBase):
    __tablename__ = "ItemFastUS"

class ItemOrderUS(Base, ItemBase):
    __tablename__ = "ItemOrderUS"

# --- ASIA Tables ---
class ItemFastAS(Base, ItemBase):
    __tablename__ = "ItemFastAS"

class ItemOrderAS(Base, ItemBase):
    __tablename__ = "ItemOrderAS"


# --- HELPER MAPPING ---
# This allows dynamic lookup: MODEL_MAP['EU']['fast'] -> ItemFastEU
MODEL_MAP = {
    "EU": {"fast": ItemFastEU, "order": ItemOrderEU},
    "US": {"fast": ItemFastUS, "order": ItemOrderUS},
    "AS": {"fast": ItemFastAS, "order": ItemOrderAS},
}

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