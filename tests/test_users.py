import pytest
from datetime import datetime, timedelta, timezone

@pytest.mark.asyncio
async def test_create_user_and_invoice(client):
    # 1. Create User
    user_data = {
        "username": "trader_joe",
        "email": "joe@test.com",
        "password": "secretpassword"
    }
    res = await client.post("/users/", json=user_data)
    assert res.status_code == 200
    user_id = res.json()["id"]

    # 2. Create Invoice
    invoice_data = {
        "amount": 15.00,
        "currency": "USD",
        "subscription_plan": "Pro"
    }
    inv_res = await client.post(f"/users/{user_id}/invoices/", json=invoice_data)
    
    assert inv_res.status_code == 200
    data = inv_res.json()
    
    assert data["status"] == "pending"
    assert data["user_id"] == user_id
    # The API returns the ORM model, which uses 'price_amount', not 'amount'
    assert data["price_amount"] == 15.00

@pytest.mark.asyncio
async def test_subscription_logic(client):
    # 1. Create User
    res = await client.post("/users/", json={
        "username": "sub_user", 
        "email": "sub@test.com", 
        "password": "pass"
    })
    user_id = res.json()["id"]

    # 2. Add 30 Days Subscription
    sub_res = await client.post(f"/users/{user_id}/subscription/add", json={"days": 30})
    assert sub_res.status_code == 200
    
    # Parse date string
    sub_until = datetime.fromisoformat(sub_res.json()["subscribed_until"])
    
    # Strict timezone comparison
    now_utc = datetime.now(timezone.utc)
    
    assert sub_until > now_utc + timedelta(days=29)

    # 3. Add another 30 Days (Should Extend)
    sub_res_2 = await client.post(f"/users/{user_id}/subscription/add", json={"days": 30})
    sub_until_2 = datetime.fromisoformat(sub_res_2.json()["subscribed_until"])
    
    assert sub_until_2 > now_utc + timedelta(days=59)