from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models, dependencies

app = FastAPI()

# --- Endpoints for Trade Bot Data ---
@app.get("/items/{item_name}")
async def get_item_prices(
    item_name: str, 
    db: AsyncSession = Depends(dependencies.get_trade_db)
):
    query = select(models.Item).where(models.Item.unique_name == item_name)
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# --- Endpoints for User Data ---
@app.post("/invoices/")
async def create_invoice(
    user_id: str, 
    amount: str,
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    new_invoice = models.Invoice(
        user_id=user_id,
        amount=amount,
        status="pending",
        currency="USD"
    )
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)
    return new_invoice