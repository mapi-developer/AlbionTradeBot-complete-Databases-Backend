from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from typing import List, Optional, Literal
from datetime import datetime, timedelta, timezone
import random 

import models, dependencies
from schemas import *
from buffer import price_buffer
from database import trade_bot_engine, crypto_backend_engine
import auth
import payments

# --- LIFESPAN (Startup & Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Service is starting...")
    yield 
    print("Shutdown: Closing database connections...")
    await trade_bot_engine.dispose()
    await crypto_backend_engine.dispose()

app = FastAPI(title="Trade Bot & Crypto Backend", lifespan=lifespan)

app.include_router(auth.router, tags=["Auth"])
app.include_router(payments.router, tags=["Payments"])

@app.get("/", tags=["System"])
async def health_check():
    return {"status": "alive", "service": "Albion Trade Bot Backend"}

def hash_password(plain_password: str) -> str:
    return f"hashed_{plain_password}"

# ==========================================
# TRADE BOT ENDPOINTS (DB 1)
# ==========================================

ServerType = Literal["EU", "US", "AS"]
ItemType = Literal["fast", "order"]

@app.put("/items/prices", tags=["Trade Bot"])
async def update_price(
    updates: List[ItemPriceUpdate],
    server: ServerType = Query(..., description="Server Region: EU, US, or AS"),
    type: ItemType = Query(..., description="Type of item price: 'fast' or 'order'")
):
    await price_buffer.add_updates(server, type, updates)
    return {"message": "Updates queued", "server": server, "type": type}

@app.post("/system/flush-buffer", tags=["System"])
async def flush_buffer_endpoint(
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    count = await price_buffer.flush(db)
    if count == 0:
        return {"status": "skipped", "message": "Buffers were empty"}
    return {"status": "success", "flushed_items": count}

@app.get("/items/", tags=["Trade Bot"])
async def get_prices(
    server: ServerType = Query(..., description="Server Region: EU, US, or AS"),
    item_names: Optional[List[str]] = Query(None),
    cities: Optional[List[str]] = Query(None, description="List of cities (e.g. 'lymhurst')"),
    type: ItemType = Query("fast", description="Which table to query"),
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    # Select the correct model dynamically
    target_model = models.MODEL_MAP[server][type]
    
    selected_columns = [target_model.unique_name]
    
    if cities:
        for city in cities:
            city_slug = city.lower().replace(" ", "_")
            price_col = getattr(target_model, f"price_{city_slug}", None)
            updated_col = getattr(target_model, f"{city_slug}_updated_at", None)

            if not price_col:
                raise HTTPException(status_code=400, detail=f"Invalid city: {city}")

            selected_columns.append(price_col)
            selected_columns.append(updated_col)
            
        stmt = select(*selected_columns)
    else:
        stmt = select(target_model)

    if item_names:
        stmt = stmt.where(target_model.unique_name.in_(item_names))
    
    result = await db.execute(stmt)

    if cities:
        data = []
        rows = result.all()
        for row in rows:
            item_data = {"unique_name": row[0]}
            current_idx = 1 
            for city in cities:
                city_slug = city.lower().replace(" ", "_")
                item_data[f"price_{city_slug}"] = row[current_idx]
                item_data[f"{city_slug}_updated_at"] = row[current_idx + 1]
                current_idx += 2
            data.append(item_data)
        return data
    else:
        return result.scalars().all()

@app.get("/items/prices-up-to-date", tags=["Trade Bot"])
async def get_prices_up_to_date(
    server: ServerType = Query(..., description="Server Region: EU, US, or AS"),
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    """
    Returns update stats for the specified server.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=8)
    cities = [
        "black_market", "caerleon", "lymhurst", "bridgewatch", 
        "fort_sterling", "thetford", "martlock", "brecilien"
    ]

    # Dynamically pick models
    ModelFast = models.MODEL_MAP[server]["fast"]
    ModelOrder = models.MODEL_MAP[server]["order"]

    def build_stats_query(model):
        selections = []
        for city in cities:
            price_col = getattr(model, f"price_{city}")
            updated_col = getattr(model, f"{city}_updated_at")
            
            selections.append(func.count(price_col))
            selections.append(
                func.sum(
                    case(
                        (and_(price_col.is_not(None), updated_col >= cutoff_time), 1), 
                        else_=0
                    )
                )
            )
        return select(*selections)

    res_fast = await db.execute(build_stats_query(ModelFast))
    row_fast = res_fast.one()
    res_order = await db.execute(build_stats_query(ModelOrder))
    row_order = res_order.one()

    response_data = {}

    for i, city in enumerate(cities):
        idx_total = i * 2
        idx_recent = i * 2 + 1

        fast_total = row_fast[idx_total] or 0
        fast_recent = row_fast[idx_recent] or 0
        order_total = row_order[idx_total] or 0
        order_recent = row_order[idx_recent] or 0

        combined_total_valid = fast_total + order_total
        combined_recent_valid = fast_recent + order_recent

        if combined_total_valid == 0:
            response_data[city] = "0%"
        else:
            percent = (combined_recent_valid / combined_total_valid) * 100
            response_data[city] = f"{int(percent)}%"

    return response_data

# ==========================================
# USER & INVOICE ENDPOINTS (DB 2)
# ==========================================

# --- User Management ---
@app.post("/users/", response_model=UserResponse, tags=["Users"])
async def create_user(
    user: UserCreate, 
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
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

    # Generate ID manually because Invoice.id is BigInteger (External ID)
    generated_id = random.getrandbits(32)

    new_invoice = models.Invoice(
        id=generated_id,
        user_id=user_id,
        price_amount=invoice_data.amount,    # Map 'amount' -> 'price_amount'
        pay_currency=invoice_data.currency,  # Map 'currency' -> 'pay_currency'
        status="pending",
        # subscription_plan is NOT in models.Invoice, so we skip it
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