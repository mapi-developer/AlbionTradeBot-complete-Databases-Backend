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
    price_brecilien: Optional[int] = None

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

class PaymentRequest(BaseModel):
    plan_id: str  # e.g., "1_month"

class PaymentResponse(BaseModel):
    invoice_url: str