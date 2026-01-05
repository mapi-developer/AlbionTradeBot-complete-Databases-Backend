import pytest
from sqlalchemy import text
from main import price_buffer

@pytest.mark.asyncio
async def test_update_price_flow_fast(client, trade_db_engine):
    """
    Test flow for 'fast' items: User pushes update -> Buffer -> Flush -> DB (ItemFast) updated.
    """
    # 1. SEED DATA (ItemFast)
    async with trade_db_engine.begin() as conn:
        await conn.execute(text("INSERT INTO ItemFast (unique_name) VALUES ('T4_SWORD')"))

    # 2. Clear buffer
    price_buffer._buffers["fast"].clear()

    # 3. Send Price Update (type=fast)
    payload = [{
        "unique_name": "T4_SWORD",
        "price_caerleon": 1000,
        "price_martlock": 2000
    }]
    response = await client.put("/items/prices", params={"type": "fast"}, json=payload)
    assert response.status_code == 200

    # 4. Trigger Flush
    flush_res = await client.post("/system/flush-buffer")
    assert flush_res.status_code == 200
    assert flush_res.json()["flushed_items"] > 0

    # 5. Verify Data (ItemFast)
    final_res = await client.get("/items/", params={"item_names": ["T4_SWORD"], "type": "fast"})
    items = final_res.json()
    assert len(items) > 0
    item = items[0]
    
    assert item["unique_name"] == "T4_SWORD"
    assert item["price_caerleon"] == 1000
    assert item["price_martlock"] == 2000

@pytest.mark.asyncio
async def test_update_price_flow_order(client, trade_db_engine):
    """
    Test flow for 'order' items: User pushes update -> Buffer -> Flush -> DB (ItemOrder) updated.
    """
    # 1. SEED DATA (ItemOrder)
    async with trade_db_engine.begin() as conn:
        await conn.execute(text("INSERT INTO ItemOrder (unique_name) VALUES ('T4_BOW')"))

    # 2. Clear buffer
    price_buffer._buffers["order"].clear()

    # 3. Send Price Update (type=order)
    payload = [{
        "unique_name": "T4_BOW",
        "price_lymhurst": 500
    }]
    response = await client.put("/items/prices", params={"type": "order"}, json=payload)
    assert response.status_code == 200

    # 4. Trigger Flush
    flush_res = await client.post("/system/flush-buffer")
    assert flush_res.status_code == 200

    # 5. Verify Data (ItemOrder)
    final_res = await client.get("/items/", params={"item_names": ["T4_BOW"], "type": "order"})
    items = final_res.json()
    assert len(items) > 0
    
    assert items[0]["unique_name"] == "T4_BOW"
    assert items[0]["price_lymhurst"] == 500

@pytest.mark.asyncio
async def test_buffer_merging(client, trade_db_engine):
    """
    Ensure multiple updates to the same item in the buffer are merged before flushing.
    """
    # 1. SEED DATA
    async with trade_db_engine.begin() as conn:
        await conn.execute(text("INSERT INTO ItemFast (unique_name) VALUES ('T4_SHIELD')"))

    price_buffer._buffers["fast"].clear()

    # User 1 sends Caerleon price
    await client.put("/items/prices", params={"type": "fast"}, json=[{
        "unique_name": "T4_SHIELD",
        "price_caerleon": 500
    }])

    # User 2 sends Martlock price (same item)
    await client.put("/items/prices", params={"type": "fast"}, json=[{
        "unique_name": "T4_SHIELD",
        "price_martlock": 600
    }])

    # Flush
    await client.post("/system/flush-buffer")

    # Check DB
    res = await client.get("/items/", params={"item_names": ["T4_SHIELD"], "type": "fast"})
    data = res.json()[0]
    
    assert data["price_caerleon"] == 500
    assert data["price_martlock"] == 600

@pytest.mark.asyncio
async def test_get_prices_city_filter(client, trade_db_engine):
    """
    Test that the 'city' parameter correctly filters the response fields.
    """
    # 1. SEED DATA
    async with trade_db_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO ItemFast (unique_name, price_lymhurst, price_thetford) VALUES ('T4_HELM', 300, 400)"
        ))

    # 2. Get with City Filter
    res = await client.get("/items/", params={"item_names": ["T4_HELM"], "city": "lymhurst", "type": "fast"})
    assert res.status_code == 200
    data = res.json()[0]

    # 3. Verify Structure
    assert "unique_name" in data
    assert "price_lymhurst" in data
    assert data["price_lymhurst"] == 300
    assert "price_thetford" not in data