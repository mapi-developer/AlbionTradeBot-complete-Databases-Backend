import pytest
from sqlalchemy import text
from main import price_buffer

# PASS 'trade_db_engine' AS AN ARGUMENT
@pytest.mark.asyncio
async def test_update_price_flow(client, trade_db_engine):
    """
    Test the full flow: User pushes update -> Buffer -> Scheduler flushes -> DB updated.
    """
    # 1. SEED DATA using the injected engine fixture
    async with trade_db_engine.begin() as conn:
        await conn.execute(text("INSERT OR IGNORE INTO Item (unique_name) VALUES ('T4_SWORD')"))

    # 2. Clear buffer
    price_buffer._buffer.clear()

    # 3. Send Price Update
    payload = [{
        "unique_name": "T4_SWORD",
        "price_caerleon": 1000,
        "price_martlock": 2000
    }]
    response = await client.put("/items/prices", json=payload)
    assert response.status_code == 200

    # 4. Trigger Flush
    flush_res = await client.post("/system/flush-buffer")
    assert flush_res.status_code == 200

    # 5. Verify Data
    final_res = await client.get("/items/?item_names=T4_SWORD")
    item = final_res.json()[0] 
    
    assert item["unique_name"] == "T4_SWORD"
    assert item["price_caerleon"] == 1000

# PASS 'trade_db_engine' AS AN ARGUMENT
@pytest.mark.asyncio
async def test_buffer_merging(client, trade_db_engine):
    # 1. SEED DATA
    async with trade_db_engine.begin() as conn:
        await conn.execute(text("INSERT OR IGNORE INTO Item (unique_name) VALUES ('T4_SHIELD')"))

    price_buffer._buffer.clear()

    # User 1 sends Caerleon price
    await client.put("/items/prices", json=[{
        "unique_name": "T4_SHIELD",
        "price_caerleon": 500
    }])

    # User 2 sends Martlock price (same item)
    await client.put("/items/prices", json=[{
        "unique_name": "T4_SHIELD",
        "price_martlock": 600
    }])

    # Flush
    await client.post("/system/flush-buffer")

    # Check DB
    res = await client.get("/items/?item_names=T4_SHIELD")
    data = res.json()[0]
    
    assert data["price_caerleon"] == 500
    assert data["price_martlock"] == 600