import hmac, hashlib, json
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone

import models, dependencies, schemas
import httpx
import os

router = APIRouter(prefix="/payments", tags=["Payments"])

PLANS = {
    "1_week": {"price": 14.99, "days": 7},
    "1_month": {"price": 49.99, "days": 30},
    "3_months": {"price": 124.99, "days": 90},
}

@router.get("/plans", tags=["Payments"])
async def get_payment_plans():
    """
    Returns the list of available subscription plans.
    """
    return PLANS

@router.post("/create", response_model=schemas.PaymentResponse)
async def create_payment(
    plan_data: schemas.PaymentRequest, 
    user_id: int, 
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    if plan_data.plan_id not in PLANS:
        raise HTTPException(400, "Invalid Plan")
    
    plan = PLANS[plan_data.plan_id]
    
    # NOWPayments API Call
    url = "https://api.nowpayments.io/v1/invoice"
    # Ensure this env var is set
    headers = {"x-api-key": os.getenv("NOWPAYMENTS_API_KEY")}
    payload = { 
        "price_amount": plan['price'],
        "price_currency": "usd",
        "order_id": f"{user_id}::{plan['days']}", # encoding info in order_id
        "ipn_callback_url": "https://trade-backend-service-1054089939982.europe-west4.run.app/payments/webhook"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json()

    # Create Invoice (formerly Payment)
    # Using 'id' from NOWPayments as the primary key or unique identifier
    new_invoice = models.Invoice(
        id=int(data['id']), 
        user_id=user_id,
        status="waiting",
        price_amount=plan['price'],
        pay_currency="usd" 
    )
    db.add(new_invoice)
    await db.commit()
    
    return {"invoice_url": data['invoice_url']}

@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(dependencies.get_crypto_db)):
    sig = request.headers.get('x-nowpayments-sig')
    body = await request.body()
    data_json = await request.json()
    sorted_data = json.dumps(data_json, separators=(',', ':'), sort_keys=True)
    
    # Verify signature
    calc_sig = hmac.new(
        os.getenv("NOWPAYMENTS_IPN_SECRET").encode(), 
        sorted_data.encode(), 
        hashlib.sha512
    ).hexdigest()
    
    if sig != calc_sig:
        raise HTTPException(403, "Invalid Signature")

    # Process Payment
    if data_json.get('payment_status') == 'finished':
        payment_id = int(data_json.get('id')) # The NOWPayments Invoice ID
        
        # 1. Update Invoice Status to "done"
        stmt = (
            update(models.Invoice)
            .where(models.Invoice.id == payment_id)
            .values(status="done")
        )
        await db.execute(stmt)

        # 2. Update User Subscription
        # Parse user_id and days from order_id passed earlier
        user_id, days = map(int, data_json.get('order_id').split("::"))
        
        res = await db.execute(select(models.User).where(models.User.id == user_id))
        user = res.scalar_one_or_none()
        
        if user:
            now = datetime.now(timezone.utc)
            current = user.subscribed_until.replace(tzinfo=timezone.utc) if user.subscribed_until else now
            
            # Stack subscription time
            if current > now:
                user.subscribed_until = current + timedelta(days=days)
            else:
                user.subscribed_until = now + timedelta(days=days)
            
        await db.commit()

    return {"status": "ok"}