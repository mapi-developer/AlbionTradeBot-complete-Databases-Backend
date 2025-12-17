from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

# --- Trade Schemas ---
class ItemPriceUpdate(BaseModel):
    unique_name: str
    price_black_market: Optional[int] = None
    price_caerleon: Optional[int] = None
    price_lymhurst: Optional[int] = None
    price_bridgewatch: Optional[int] = None
    price_fort_sterling: Optional[int] = None
    price_thetford: Optional[int] = None
    price_martlock: Optional[int] = None

class HistoryUpdate(BaseModel):
    unique_name: str

    black_market_day: Optional[int] = None
    black_market_week: Optional[int] = None
    black_market_month: Optional[int] = None    
    caerleon_day: Optional[int] = None
    caerleon_week: Optional[int] = None
    caerleon_month: Optional[int] = None
    lymhurst_day: Optional[int] = None
    lymhurst_week: Optional[int] = None
    lymhurst_month: Optional[int] = None
    bridgewatch_day: Optional[int] = None
    bridgewatch_week: Optional[int] = None
    bridgewatch_month: Optional[int] = None
    fort_sterling_day: Optional[int] = None
    fort_sterling_week: Optional[int] = None
    fort_sterling_month: Optional[int] = None
    thetford_day: Optional[int] = None
    thetford_week: Optional[int] = None
    thetford_month: Optional[int] = None
    martlock_day: Optional[int] = None
    martlock_week: Optional[int] = None
    martlock_month: Optional[int] = None

# --- User Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: Optional[str] = None
    google_id: Optional[str] = None
    discord_id: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    google_id: Optional[str] = None
    discord_id: Optional[str] = None
    profile_picture: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    subscribed_until: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class SubscriptionAdd(BaseModel):
    days: int

# --- Invoice Schemas ---
class InvoiceCreate(BaseModel):
    amount: float
    currency: str = "USD"
    subscription_plan: str = "1_month"