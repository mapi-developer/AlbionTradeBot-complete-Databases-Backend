from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime, timedelta, timezone

import models, dependencies
from schemas import *
from buffer import price_buffer
from database import trade_bot_engine, crypto_backend_engine

# --- LIFESPAN (Startup & Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # REMOVE the create_all logic here!
    # It is already handled by reset_db.py in the Cloud Build step.
    print("Startup: Service is starting...")
    
    yield  # Application runs
    
    # Shutdown: Dispose Engines
    print("Shutdown: Closing database connections...")
    await trade_bot_engine.dispose()
    await crypto_backend_engine.dispose()

# --- APP INITIALIZATION ---
# Pass the lifespan handler here instead of using on_event
app = FastAPI(title="Trade Bot & Crypto Backend", lifespan=lifespan)

# Add this to main.py
@app.get("/", tags=["System"])
async def health_check():
    return {"status": "alive", "service": "Albion Trade Bot Backend"}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def hash_password(plain_password: str) -> str:
    # TODO: Replace with 'passlib' or 'bcrypt' in production
    return f"hashed_{plain_password}"


# ==========================================
# TRADE BOT ENDPOINTS (DB 1)
# ==========================================

@app.put("/items/prices", tags=["Trade Bot"])
async def update_prices(
    updates: List[ItemPriceUpdate],
):
    """
    High-frequency endpoint. 
    Receives updates -> Pushes to Memory Buffer -> Returns OK immediately.
    """
    await price_buffer.add_updates(updates)
    return {"message": "Updates queued", "buffer_size": len(price_buffer._buffer)}

@app.post("/system/flush-buffer", tags=["System"])
async def flush_buffer_endpoint(
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    """
    CRITICAL: This is hit by Cloud Scheduler every 1 minute.
    Writes buffered data to the database in one big batch.
    """
    count = await price_buffer.flush(db)
    if count == 0:
        return {"status": "skipped", "message": "Buffer was empty"}
    return {"status": "success", "flushed_items": count}

@app.put("/items/history", tags=["Trade Bot"])
async def update_history(
    updates: List[HistoryUpdate],
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    """
    Updates average price history directly (less frequent than live prices).
    """
    count = 0
    for hist in updates:
        data = hist.dict(exclude_unset=True)
        unique_name = data.pop("unique_name")
        
        if data:
            data["updated_at"] = datetime.now(timezone.utc)
            stmt = (
                update(models.AvgPrice)
                .where(models.AvgPrice.unique_name == unique_name)
                .values(**data)
            )
            await db.execute(stmt)
            count += 1

    await db.commit()
    return {"message": f"Updated history for {count} items"}

@app.get("/items/", tags=["Trade Bot"])
async def get_prices(
    city: Optional[str] = None,
    item_names: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    stmt = select(models.Item)
    if item_names:
        stmt = stmt.where(models.Item.unique_name.in_(item_names))
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    return items

@app.get("/items/avg", tags=["Trade Bot"])
async def get_avg(
    item_names: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    stmt = select(models.AvgPrice)
    if item_names:
        stmt = stmt.where(models.AvgPrice.unique_name.in_(item_names))
    
    result = await db.execute(stmt)
    return result.scalars().all()

# ==========================================
# USER & INVOICE ENDPOINTS (DB 2)
# ==========================================

# --- User Management ---
@app.post("/users/", response_model=UserResponse, tags=["Users"])
async def create_user(
    user: UserCreate, 
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    # Check if exists
    query = select(models.User).where(
        (models.User.email == user.email) | (models.User.username == user.username)
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        joined_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user(
    user_id: int, 
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def change_info(
    user_id: int,
    info: UserUpdate,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = info.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
    
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return user

# --- Subscription Logic ---
@app.post("/users/{user_id}/subscription/add", tags=["Subscription"])
async def add_subscription(
    user_id: int,
    sub_data: SubscriptionAdd,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc)
    
    # Logic: Extend if active, Start new if expired
    if user.subscribed_until and user.subscribed_until.replace(tzinfo=timezone.utc) > now:
        user.subscribed_until = user.subscribed_until.replace(tzinfo=timezone.utc) + timedelta(days=sub_data.days)
    else:
        user.subscribed_until = now + timedelta(days=sub_data.days)
        
    await db.commit()
    return {"status": "updated", "subscribed_until": user.subscribed_until}

@app.delete("/users/{user_id}/subscription", tags=["Subscription"])
async def remove_subscription(
    user_id: int,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        user.subscribed_until = None
        await db.commit()
        
    return {"status": "removed"}

# --- Invoices ---
@app.post("/users/{user_id}/invoices/", tags=["Invoices"])
async def create_invoice(
    user_id: int, 
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    # Verify User Exists
    user_check = await db.execute(select(models.User).where(models.User.id == user_id))
    if not user_check.scalar_one_or_none():
         raise HTTPException(status_code=404, detail="User not found")

    new_invoice = models.Invoice(
        user_id=user_id,
        amount=invoice_data.amount,
        status="pending",
        currency=invoice_data.currency,
        subscription_plan=invoice_data.subscription_plan,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)
    return new_invoice

@app.get("/invoices/", tags=["Invoices"])
async def get_invoices(
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    stmt = select(models.Invoice).offset(offset).limit(limit)
    if user_id:
        stmt = stmt.where(models.Invoice.user_id == user_id)
    
    stmt = stmt.order_by(models.Invoice.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@app.get("/invoices/last", tags=["Invoices"])
async def get_last_invoices(
    count: int = 10,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    stmt = (
        select(models.Invoice)
        .order_by(models.Invoice.created_at.desc())
        .limit(count)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

