import hmac, hashlib, json
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

import models, dependencies, schemas
import httpx
import os

router = APIRouter(prefix="/payments", tags=["Payments"])

PLANS = {
    "1_week": {"price": 15.0, "days": 7},
    "1_month": {"price": 50.0, "days": 30},
    "3_month": {"price": 130.0, "days": 90},
}

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
    headers = {"x-api-key": os.getenv("NOWPAYMENTS_API_KEY")}
    payload = {
        "price_amount": plan['price'],
        "price_currency": "usd",
        "order_id": f"{user_id}::{plan['days']}",
        "ipn_callback_url": "https://trade-backend-service-1054089939982.europe-west4.run.app/payments/webhook"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json()

    new_payment = models.Payment(
        payment_id=str(data['id']),
        user_id=user_id,
        status="waiting",
        price_amount=plan['price']
    )
    db.add(new_payment)
    await db.commit()
    
    return {"invoice_url": data['invoice_url']}

@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(dependencies.get_crypto_db)):
    sig = request.headers.get('x-nowpayments-sig')
    body = await request.body()
    
    # Verify signature
    calc_sig = hmac.new(
        os.getenv("NOWPAYMENTS_IPN_SECRET").encode(), 
        body, 
        hashlib.sha512
    ).hexdigest()
    
    if sig != calc_sig:
        raise HTTPException(403, "Invalid Signature")

    data = json.loads(body)
    if data.get('payment_status') == 'finished':
        user_id, days = map(int, data.get('order_id').split("::"))
        
        # Update User Subscription (Stacking Logic)
        res = await db.execute(select(models.User).where(models.User.id == user_id))
        user = res.scalar_one_or_none()
        
        if user:
            now = datetime.now(timezone.utc)
            current = user.subscribed_until.replace(tzinfo=timezone.utc) if user.subscribed_until else now
            
            if current > now:
                user.subscribed_until = current + timedelta(days=days)
            else:
                user.subscribed_until = now + timedelta(days=days)
            
            await db.commit()

    return {"status": "ok"}